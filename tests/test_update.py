import re
from textwrap import dedent
from typing import Any

from pytest import mark, param, raises, warns

from omegaconf import ListConfig, OmegaConf, ValidationError
from omegaconf._utils import _ensure_container, is_primitive_container
from tests import Package


@mark.parametrize(
    "cfg,key,value,expected",
    [
        # dict
        param({"a": "b"}, "a", "c", {"a": "c"}, id="replace:string"),
        param({"a": "b"}, "c", "d", {"a": "b", "c": "d"}, id="add:string"),
        param({"a": "b"}, "c", None, {"a": "b", "c": None}, id="none_value"),
        param({}, "a", {}, {"a": {}}, id="dict:value:empty_dict"),
        param({}, "a", {"b": 1}, {"a": {"b": 1}}, id="value:dict"),
        param({}, "a.b", 1, {"a": {"b": 1}}, id="dict:deep"),
        param({"a": "b"}, "a.b", {"c": 1}, {"a": {"b": {"c": 1}}}, id="dict:deep:map"),
        param({}, "a", 1, {"a": 1}, id="dict:value"),
        param({}, "a.b", 1, {"a": {"b": 1}}, id="dict:deep:value"),
        param({"a": 1}, "b.c", 2, {"a": 1, "b": {"c": 2}}, id="dict:deep:value"),
        param(
            {"a": {"b": {"c": 1}}},
            "a.b.d",
            2,
            {"a": {"b": {"c": 1, "d": 2}}},
            id="deep_map_update",
        ),
        param({"a": "???"}, "a", 123, {"a": 123}, id="update_missing"),
        param({"a": None}, "a", None, {"a": None}, id="same_value"),
        param({"a": 123}, "a", 123, {"a": 123}, id="same_value"),
        param({}, "a", {}, {"a": {}}, id="dict_value"),
        param({}, "a", {"b": 1}, {"a": {"b": 1}}, id="dict_value"),
        param({"a": {"b": 2}}, "a", {"b": 1}, {"a": {"b": 1}}, id="dict_value"),
        # dict value (merge or set)
        param(
            {"a": None},
            "a",
            {"c": 2},
            {"a": {"c": 2}},
            id="dict_value:merge",
        ),
        param(
            {"a": {"b": 1}},
            "a",
            {"c": 2},
            {"a": {"b": 1, "c": 2}},
            id="dict_value:merge",
        ),
        # list
        param({"a": [1, 2]}, "a", [2, 3], {"a": [2, 3]}, id="list:replace"),
        param([1, 2, 3], "1", "abc", [1, "abc", 3], id="list:update"),
        param([1, 2, 3], "-1", "abc", [1, 2, "abc"], id="list:update"),
        param(
            {"a": {"b": [1, 2, 3]}},
            "a.b.1",
            "abc",
            {"a": {"b": [1, "abc", 3]}},
            id="list:nested:update",
        ),
        param(
            {"a": {"b": [1, 2, 3]}},
            "a.b.-1",
            "abc",
            {"a": {"b": [1, 2, "abc"]}},
            id="list:nested:update",
        ),
        param([{"a": 1}], "0", {"b": 2}, [{"a": 1, "b": 2}], id="list:merge"),
        param(
            {"list": [{"a": 1}]},
            "list",
            [{"b": 2}],
            {"list": [{"b": 2}]},
            id="list:merge",
        ),
    ],
)
def test_update(cfg: Any, key: str, value: Any, expected: Any) -> None:
    cfg = _ensure_container(cfg)
    OmegaConf.update(cfg, key, value, merge=True)
    assert cfg == expected


@mark.parametrize(
    "cfg,key,value,merge,expected",
    [
        param(
            {"a": {"b": 1}},
            "a",
            {"c": 2},
            True,
            {"a": {"b": 1, "c": 2}},
            id="dict_value:merge",
        ),
        param(
            {"a": {"b": 1}},
            "a",
            {"c": 2},
            False,
            {"a": {"c": 2}},
            id="dict_value:set",
        ),
        # merging lists is replacing.
        # this is useful when we mix it Structured Configs
        param(
            {"a": {"b": [1, 2]}},
            "a.b",
            [3, 4],
            True,
            {"a": {"b": [3, 4]}},
            id="list:merge",
        ),
        param(
            {"a": {"b": [1, 2]}},
            "a.b",
            [3, 4],
            False,
            {"a": {"b": [3, 4]}},
            id="list:set",
        ),
        param(
            Package,
            "modules",
            [{"name": "foo"}],
            True,
            {"modules": [{"name": "foo", "classes": "???"}]},
            id="structured_list:merge",
        ),
        param(
            Package,
            "modules",
            [{"name": "foo"}],
            False,
            raises(ValidationError),
            id="structured_list:set",
        ),
    ],
)
def test_update_merge_set(
    cfg: Any, key: str, value: Any, merge: bool, expected: Any
) -> None:
    cfg = _ensure_container(cfg)
    if is_primitive_container(expected):
        OmegaConf.update(cfg, key, value, merge=merge)
        assert cfg == expected
    else:
        with expected:
            OmegaConf.update(cfg, key, value, merge=merge)


def test_update_list_make_dict() -> None:
    c = OmegaConf.create([None, None])
    assert isinstance(c, ListConfig)
    OmegaConf.update(c, "0.a.a", "aa", merge=True)
    OmegaConf.update(c, "0.a.b", "ab", merge=True)
    OmegaConf.update(c, "1.b.a", "ba", merge=True)
    OmegaConf.update(c, "1.b.b", "bb", merge=True)
    assert c == [{"a": {"a": "aa", "b": "ab"}}, {"b": {"a": "ba", "b": "bb"}}]


def test_update_node_deprecated() -> None:
    c = OmegaConf.create()
    with warns(
        expected_warning=UserWarning,
        match=re.escape(
            "update_node() is deprecated, use OmegaConf.update(). (Since 2.0)"
        ),
    ):
        c.update_node("foo", "bar")
    assert c.foo == "bar"


def test_update_list_index_error() -> None:
    c = OmegaConf.create([1, 2, 3])
    assert isinstance(c, ListConfig)
    with raises(IndexError):
        OmegaConf.update(c, "4", "abc", merge=True)

    assert c == [1, 2, 3]


def test_merge_deprecation() -> None:
    cfg = OmegaConf.create({"a": {"b": 10}})
    msg = dedent(
        """\
            update() merge flag is is not specified, defaulting to False.
            For more details, see https://github.com/omry/omegaconf/issues/367"""
    )

    with warns(UserWarning, match=re.escape(msg)):
        OmegaConf.update(cfg, "a", {"c": 20})  # default to set, and issue a warning.
        assert cfg == {"a": {"c": 20}}
