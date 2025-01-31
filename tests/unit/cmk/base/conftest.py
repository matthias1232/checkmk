#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc
from unittest import mock

import pytest


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches():
    from cmk.utils.caching import cache_manager

    cache_manager.clear()


class _MockVSManager(typing.NamedTuple):
    active_service_interface: abc.Mapping[str, object]


@pytest.fixture()
def initialised_item_state():
    mock_vs = _MockVSManager({})
    with mock.patch(
        "cmk.base.api.agent_based.value_store._global_state._active_host_value_store",
        mock_vs,
    ):
        yield
