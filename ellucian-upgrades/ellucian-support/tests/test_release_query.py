"""Tests for release.py Table API queries and prerequisite extraction."""

import json
from unittest.mock import MagicMock, patch

import pytest

from ellucian_support.release import (
    BANNER_PRODUCT_LINE_ID,
    Release,
    _fetch_prerequisites,
    _get_related_ids_from_page,
    query_releases,
)


# --- Release dataclass tests ---


class TestReleaseFromApi:
    def test_basic_fields(self):
        data = {
            "sys_id": "abc123",
            "number": "PR00042966",
            "short_description": "BA FIN AID 9.3.57",
            "date_released": "2026-02-15",
            "target_ga_date": "2026-03-19",
            "description": "Maintenance release",
            "summary": "Financial Aid maintenance",
            "release_purpose": "maintenance",
            "state": "-5",
            "ellucian_product_full_hierarchy": "Banner - Financial Aid",
            "release_documentation": "https://example.com/docs",
        }
        r = Release.from_api(data)
        assert r.sys_id == "abc123"
        assert r.number == "PR00042966"
        assert r.short_description == "BA FIN AID 9.3.57"
        assert r.target_ga_date == "2026-03-19"
        assert r.release_purpose == "maintenance"
        assert r.state == "-5"
        assert r.product_hierarchy == "Banner - Financial Aid"

    def test_reference_fields_as_dicts(self):
        data = {
            "sys_id": "abc123",
            "number": "PR00042966",
            "short_description": "BA FIN AID 9.3.57",
            "ellucian_product_line": {
                "link": "https://example.com/api",
                "value": "line123",
            },
            "ellucian_product_name": {
                "link": "https://example.com/api",
                "value": "name456",
            },
            "ellucian_product_version": {
                "link": "https://example.com/api",
                "value": "ver789",
            },
        }
        r = Release.from_api(data)
        assert r.product_line == "line123"
        assert r.product_name == "name456"
        assert r.version == "ver789"


class TestReleaseToDict:
    def test_roundtrip(self):
        r = Release(
            sys_id="abc",
            number="PR001",
            short_description="BA FIN AID 9.3.57",
            target_ga_date="2026-03-19",
            release_purpose="regulatory",
            prerequisites=["BA GENERAL 8.25", "BA STUDENT 8.36"],
        )
        d = r.to_dict()
        assert d["target_ga_date"] == "2026-03-19"
        assert d["release_purpose"] == "regulatory"
        assert d["prerequisites"] == ["BA GENERAL 8.25", "BA STUDENT 8.36"]

    def test_from_dict_roundtrip(self):
        original = Release(
            sys_id="abc",
            number="PR001",
            short_description="BA FIN AID 9.3.57",
            target_ga_date="2026-03-19",
            prerequisites=["BA GENERAL 8.25"],
        )
        d = original.to_dict()
        restored = Release.from_dict(d)
        assert restored.sys_id == original.sys_id
        assert restored.short_description == original.short_description
        assert restored.target_ga_date == original.target_ga_date
        assert restored.prerequisites == original.prerequisites


# --- SP page parsing tests ---


def _make_sp_response(tabs):
    """Build a minimal SP page response with the given tabs."""
    return {
        "result": {
            "containers": [
                {
                    "rows": [
                        {
                            "columns": [
                                {
                                    "widgets": [
                                        {
                                            "widget": {
                                                "name": "Standard Ticket Tab",
                                                "data": {"tabs": tabs},
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }


def _make_tab(name, filter_str):
    return {
        "name": name,
        "widget": {
            "data": {
                "widget": {
                    "options": {"filter": filter_str},
                }
            }
        },
    }


class TestGetRelatedIdsFromPage:
    def test_extracts_all_three_types(self):
        tabs = [
            _make_tab("Related Defects", "sys_idINd1,d2,d3"),
            _make_tab("Related Enhancements", "sys_idINe1,e2"),
            _make_tab("Prerequisite Releases", "sys_idINp1,p2,p3,p4"),
        ]
        response = _make_sp_response(tabs)

        client = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = response
        client.get.return_value = resp_mock

        defect_ids, enhancement_ids, prerequisite_ids = _get_related_ids_from_page(
            client, "test_sys_id"
        )

        assert defect_ids == ["d1", "d2", "d3"]
        assert enhancement_ids == ["e1", "e2"]
        assert prerequisite_ids == ["p1", "p2", "p3", "p4"]

    def test_empty_on_no_tabs(self):
        response = _make_sp_response([])
        client = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 200
        resp_mock.json.return_value = response
        client.get.return_value = resp_mock

        d, e, p = _get_related_ids_from_page(client, "test")
        assert d == []
        assert e == []
        assert p == []

    def test_empty_on_http_error(self):
        client = MagicMock()
        resp_mock = MagicMock()
        resp_mock.status_code = 403
        client.get.return_value = resp_mock

        d, e, p = _get_related_ids_from_page(client, "test")
        assert d == []
        assert e == []
        assert p == []


class TestFetchPrerequisites:
    def test_fetches_short_descriptions(self):
        client = MagicMock()

        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "prereq1" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "result": {"short_description": "BA GENERAL 8.25"}
                }
            elif "prereq2" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "result": {"short_description": "BA STUDENT 8.36"}
                }
            else:
                resp.status_code = 404
            return resp

        client.get.side_effect = mock_get

        result = _fetch_prerequisites(client, ["prereq1", "prereq2", "missing"])
        assert result == ["BA GENERAL 8.25", "BA STUDENT 8.36"]

    def test_empty_list(self):
        client = MagicMock()
        result = _fetch_prerequisites(client, [])
        assert result == []


# --- query_releases tests ---


class TestQueryReleases:
    @patch("ellucian_support.release._make_client")
    def test_returns_releases(self, mock_make_client):
        mock_client = MagicMock()
        mock_make_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_make_client.return_value.__exit__ = MagicMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "result": [
                {
                    "sys_id": "abc",
                    "number": "PR001",
                    "short_description": "BA FIN AID 9.3.57",
                    "target_ga_date": "2026-03-19",
                    "state": "-5",
                },
                {
                    "sys_id": "def",
                    "number": "PR002",
                    "short_description": "BA GENERAL 8.26",
                    "target_ga_date": "2026-03-19",
                    "state": "-5",
                },
            ]
        }
        mock_client.get.return_value = mock_resp

        session = MagicMock()
        session.cookies = {}
        releases = query_releases(session, "target_ga_date<=2026-03-19")

        assert len(releases) == 2
        assert releases[0].short_description == "BA FIN AID 9.3.57"
        assert releases[1].short_description == "BA GENERAL 8.26"

    @patch("ellucian_support.release._make_client")
    def test_raises_on_error(self, mock_make_client):
        mock_client = MagicMock()
        mock_make_client.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_make_client.return_value.__exit__ = MagicMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client.get.return_value = mock_resp

        session = MagicMock()
        session.cookies = {}
        with pytest.raises(Exception, match="HTTP 401"):
            query_releases(session, "some_query")
