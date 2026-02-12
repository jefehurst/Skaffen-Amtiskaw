"""Tests for confluence.py — XML rendering and page publishing."""

from unittest.mock import MagicMock, patch

import pytest

from ellucian_support.confluence import (
    ConfluenceError,
    _detail_page_title,
    _format_date,
    _release_type_label,
    _version_from_short_desc,
    compute_client_status,
    create_page,
    render_client_page,
    render_detail_page,
    render_root_page,
    render_status_page,
)
from ellucian_support.release import Defect, Enhancement, Release
from ellucian_support.upgrade import UpgradeModule, UpgradeRound


# --- Helper function tests ---


class TestVersionFromShortDesc:
    def test_extracts_version(self):
        assert _version_from_short_desc("BA FIN AID 9.3.57") == "9.3.57"

    def test_multi_part_version(self):
        assert _version_from_short_desc("BA GENERAL CMN DB 9.41") == "9.41"

    def test_no_version(self):
        assert _version_from_short_desc("BA FIN AID") == "BA FIN AID"


class TestFormatDate:
    def test_iso_date(self):
        assert _format_date("2026-03-19") == "03-19"

    def test_datetime(self):
        assert _format_date("2026-03-19 00:00:00") == "03-19"

    def test_empty(self):
        assert _format_date("") == ""


class TestReleaseTypeLabel:
    def test_defect_only(self):
        r = Release(
            sys_id="a", number="PR1", short_description="test",
            defects=[Defect(sys_id="d1", number="PD1", summary="bug")],
        )
        assert _release_type_label(r) == "Defect"

    def test_enhancement_only(self):
        r = Release(
            sys_id="a", number="PR1", short_description="test",
            enhancements=[Enhancement(sys_id="e1", number="EN1", summary="feat")],
        )
        assert _release_type_label(r) == "Enhancement"

    def test_regulatory(self):
        r = Release(
            sys_id="a", number="PR1", short_description="test",
            release_purpose="regulatory",
        )
        assert _release_type_label(r) == "Regulatory"

    def test_combined(self):
        r = Release(
            sys_id="a", number="PR1", short_description="test",
            release_purpose="regulatory",
            defects=[Defect(sys_id="d1", number="PD1", summary="bug")],
            enhancements=[Enhancement(sys_id="e1", number="EN1", summary="feat")],
        )
        assert _release_type_label(r) == "Defect/Enhancement/Regulatory"

    def test_empty(self):
        r = Release(sys_id="a", number="PR1", short_description="test")
        assert _release_type_label(r) == ""


class TestDetailPageTitle:
    def test_single_version(self):
        mod = UpgradeModule(
            name="BA FIN AID",
            releases=[
                Release(sys_id="a", number="PR1", short_description="BA FIN AID 9.3.57"),
            ],
        )
        assert _detail_page_title(mod) == "BA FIN AID 9.3.57"

    def test_multiple_versions(self):
        mod = UpgradeModule(
            name="BA FIN AID",
            releases=[
                Release(sys_id="a", number="PR1", short_description="BA FIN AID 8.56"),
                Release(sys_id="b", number="PR2", short_description="BA FIN AID 9.3.57"),
            ],
        )
        assert _detail_page_title(mod) == "BA FIN AID 8.56/9.3.57"


# --- Root page rendering tests ---


class TestRenderRootPage:
    def _make_round(self):
        return UpgradeRound(
            title="Spring 2026",
            cutoff_date="2026-03-19",
            modules=[
                UpgradeModule(
                    name="BA FIN AID",
                    releases=[
                        Release(
                            sys_id="abc",
                            number="PR001",
                            short_description="BA FIN AID 9.3.57",
                            target_ga_date="2026-03-19",
                            prerequisites=["BA GENERAL 8.25", "BA STUDENT 8.36"],
                        ),
                    ],
                ),
                UpgradeModule(
                    name="BA GENERAL",
                    releases=[
                        Release(
                            sys_id="def",
                            number="PR002",
                            short_description="BA GENERAL 8.26",
                            target_ga_date="2026-03-19",
                            defects=[Defect(sys_id="d1", number="PD1", summary="fix")],
                        ),
                    ],
                ),
            ],
        )

    def test_contains_layout(self):
        html = render_root_page(self._make_round())
        assert "<ac:layout>" in html
        assert "</ac:layout>" in html

    def test_contains_synopsis(self):
        html = render_root_page(self._make_round())
        assert "<strong>Synopsis</strong>" in html
        assert "Spring 2026" in html

    def test_contains_details_table(self):
        html = render_root_page(self._make_round())
        assert "<strong>Module</strong>" in html
        assert "<strong>Latest Version</strong>" in html
        assert "<strong>Dependencies</strong>" in html

    def test_contains_module_rows(self):
        html = render_root_page(self._make_round())
        assert "BA FIN AID" in html
        assert "9.3.57" in html
        assert "BA GENERAL" in html
        assert "8.26" in html

    def test_contains_dependencies(self):
        html = render_root_page(self._make_round())
        assert "BA GENERAL 8.25" in html
        assert "BA STUDENT 8.36" in html

    def test_contains_timeline(self):
        html = render_root_page(self._make_round())
        assert "UPGR" in html
        assert "TEST" in html
        assert "PROD" in html
        assert "DEVL" in html

    def test_detail_links(self):
        links = {"BA FIN AID": "https://example.com/wiki/x/ABC"}
        html = render_root_page(self._make_round(), detail_links=links)
        assert 'href="https://example.com/wiki/x/ABC"' in html
        assert ">9.3.57</a>" in html

    def test_module_name_only_on_first_row(self):
        round_ = UpgradeRound(
            title="Test",
            cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(
                    name="BA FIN AID",
                    releases=[
                        Release(sys_id="a", number="PR1", short_description="BA FIN AID 8.56"),
                        Release(sys_id="b", number="PR2", short_description="BA FIN AID 9.3.57"),
                    ],
                ),
            ],
        )
        html = render_root_page(round_)
        # Module name should appear in first row, empty <p /> in second
        assert html.count("<p>BA FIN AID</p>") == 1  # Module name once in Details


# --- Detail page rendering tests ---


class TestRenderDetailPage:
    def _make_module(self):
        return UpgradeModule(
            name="BA FIN AID",
            releases=[
                Release(
                    sys_id="abc",
                    number="PR001",
                    short_description="BA FIN AID 9.3.57",
                    summary="Financial Aid maintenance release",
                    defects=[
                        Defect(sys_id="d1", number="PD00012345", summary="Fix for FAFSA"),
                        Defect(sys_id="d2", number="PD00012346", summary="Fix for awards"),
                    ],
                    enhancements=[
                        Enhancement(sys_id="e1", number="EN00006789", summary="ISIR improvements"),
                    ],
                ),
            ],
        )

    def test_contains_layout(self):
        html = render_detail_page(self._make_module())
        assert "<ac:layout>" in html
        assert "</ac:layout>" in html

    def test_contains_synopsis(self):
        html = render_detail_page(self._make_module())
        assert "<strong>Synopsis</strong>" in html
        assert "Financial Aid maintenance release" in html

    def test_contains_upgrade_notes_panel(self):
        html = render_detail_page(self._make_module())
        assert '<ac:structured-macro ac:name="panel"' in html
        assert "<strong>Upgrade Notes</strong>" in html

    def test_contains_enhancement_table(self):
        html = render_detail_page(self._make_module())
        assert "<h3>Enhancements</h3>" in html
        assert "<strong>Module/Version</strong>" in html
        assert "<strong>Change Request</strong>" in html
        assert "EN00006789" in html
        assert "ISIR improvements" in html

    def test_contains_defect_table(self):
        html = render_detail_page(self._make_module())
        assert "<h3>Defects</h3>" in html
        assert "PD00012345" in html
        assert "Fix for FAFSA" in html
        assert "PD00012346" in html

    def test_defect_links(self):
        html = render_detail_page(self._make_module())
        assert "table=ellucian_product_defect" in html
        assert "sys_id=d1" in html

    def test_enhancement_links(self):
        html = render_detail_page(self._make_module())
        assert "table=ellucian_product_enhancement" in html
        assert "sys_id=e1" in html

    def test_empty_module(self):
        mod = UpgradeModule(
            name="BA TEST",
            releases=[
                Release(sys_id="a", number="PR1", short_description="BA TEST 1.0"),
            ],
        )
        html = render_detail_page(mod)
        # Should have placeholder empty rows
        assert "<h3>Enhancements</h3>" in html
        assert "<h3>Defects</h3>" in html

    def test_version_in_table_rows(self):
        html = render_detail_page(self._make_module())
        assert "<p>9.3.57</p>" in html


# --- API tests ---


class TestCreatePage:
    @patch("ellucian_support.confluence.httpx.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "12345",
            "title": "Test Page",
            "_links": {"tinyui": "/wiki/x/ABC"},
        }
        mock_client.post.return_value = mock_resp

        result = create_page(
            "Test Page", "space123", "parent456",
            "<p>body</p>", "user@test.com", "token", "test.atlassian.net",
        )

        assert result["id"] == "12345"
        mock_client.post.assert_called_once()

    @patch("ellucian_support.confluence.httpx.Client")
    def test_failure_raises(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_client.post.return_value = mock_resp

        with pytest.raises(ConfluenceError, match="HTTP 400"):
            create_page(
                "Test", "space", "parent",
                "<p>body</p>", "user", "token", "test.atlassian.net",
            )


# --- Client page rendering tests ---


class TestRenderClientPage:
    def _make_round(self):
        return UpgradeRound(
            title="Spring 2026",
            cutoff_date="2026-03-19",
            modules=[
                UpgradeModule(
                    name="BA FIN AID",
                    releases=[
                        Release(
                            sys_id="abc",
                            number="PR001",
                            short_description="BA FIN AID 9.3.57",
                            target_ga_date="2026-03-19",
                            prerequisites=["BA GENERAL 8.25"],
                        ),
                    ],
                ),
                UpgradeModule(
                    name="BA GENERAL CMN DB",
                    releases=[
                        Release(
                            sys_id="def",
                            number="PR002",
                            short_description="BA GENERAL CMN DB 9.41",
                            target_ga_date="2026-03-19",
                            defects=[Defect(sys_id="d1", number="PD1", summary="fix")],
                        ),
                    ],
                ),
                UpgradeModule(
                    name="BA FINANCE",
                    releases=[
                        Release(
                            sys_id="ghi",
                            number="PR003",
                            short_description="BA FINANCE 9.14",
                            target_ga_date="2026-02-15",
                        ),
                    ],
                ),
            ],
        )

    def _installed(self):
        return {
            "BA FIN AID": "9.3.56",
            "BA GENERAL CMN DB": "9.40",
            # BA FINANCE not installed — should be excluded
        }

    def _detail_links(self):
        return {
            "BA FIN AID": "https://example.com/wiki/x/FINAID",
            "BA GENERAL CMN DB": "https://example.com/wiki/x/GENDB",
            "BA FINANCE": "https://example.com/wiki/x/FIN",
        }

    def test_contains_layout(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "<ac:layout>" in html
        assert "</ac:layout>" in html

    def test_contains_six_column_headers(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "<strong>Module</strong>" in html
        assert "<strong>Current Version</strong>" in html
        assert "<strong>Latest Version</strong>" in html
        assert "<strong>Release Date</strong>" in html
        assert "<strong>Defect/Enhancement/Regulatory</strong>" in html
        assert "<strong>Dependencies</strong>" in html

    def test_only_includes_installed_modules(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "BA FIN AID" in html
        assert "BA GENERAL CMN DB" in html
        # BA FINANCE is NOT installed, should NOT appear
        assert "BA FINANCE" not in html

    def test_shows_current_version(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "9.3.56" in html  # Current version for BA FIN AID
        assert "9.40" in html    # Current version for BA GENERAL CMN DB

    def test_shows_latest_version(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "9.3.57" in html  # Latest version for BA FIN AID
        assert "9.41" in html    # Latest version for BA GENERAL CMN DB

    def test_detail_links_on_latest_version(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert 'href="https://example.com/wiki/x/FINAID"' in html
        assert 'href="https://example.com/wiki/x/GENDB"' in html

    def test_contains_dependencies(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "BA GENERAL 8.25" in html

    def test_contains_title_in_synopsis(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
            client_name="FHDA",
        )
        assert "FHDA" in html
        assert "Spring 2026" in html

    def test_contains_timeline(self):
        html = render_client_page(
            self._make_round(), self._installed(), self._detail_links(),
        )
        assert "UPGR" in html
        assert "TEST" in html
        assert "PROD" in html
        assert "DEVL" in html

    def test_empty_installed_versions(self):
        html = render_client_page(
            self._make_round(), {}, self._detail_links(),
        )
        # Should have no module rows but still valid structure
        assert "<strong>Module</strong>" in html
        # None of the module names should appear in the Details table
        assert "BA FIN AID" not in html

    def test_module_name_only_on_first_row(self):
        """Multi-release module shows name only once."""
        round_ = UpgradeRound(
            title="Test",
            cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(
                    name="BA FIN AID",
                    releases=[
                        Release(sys_id="a", number="PR1", short_description="BA FIN AID 8.56"),
                        Release(sys_id="b", number="PR2", short_description="BA FIN AID 9.3.57"),
                    ],
                ),
            ],
        )
        installed = {"BA FIN AID": "8.55"}
        html = render_client_page(round_, installed, {})
        # Module name should appear once in the Details table, plus once in synopsis
        # Count in table rows specifically: should only have 1 <p>BA FIN AID</p>
        assert html.count("<p>BA FIN AID</p>") == 1

    def test_dual_track_releases_both_shown(self):
        """Modules with both 8.x and 9.x releases show all — tracks are complementary."""
        round_ = UpgradeRound(
            title="Test",
            cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(
                    name="BA CALBHR",
                    releases=[
                        Release(sys_id="a", number="PR1", short_description="BA CALBHR 8.28",
                                target_ga_date="2026-01-15"),
                        Release(sys_id="b", number="PR2", short_description="BA CALBHR 9.3.56",
                                target_ga_date="2026-02-15"),
                    ],
                ),
            ],
        )
        installed = {"BA CALBHR": "9.3.55.0.1"}
        html = render_client_page(round_, installed, {})
        # Both tracks should be shown — they are complementary
        assert "8.28" in html
        assert "9.3.56" in html
        assert "9.3.55.0.1" in html


# --- Status page tests ---


class TestComputeClientStatus:
    def test_all_current_is_green(self):
        """Client with no releases behind should be green."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name="BA FIN AID", releases=[
                    Release(sys_id="a", number="PR1",
                            short_description="BA FIN AID 9.3.57"),
                ]),
            ],
        )
        # Module exists but no releases are behind (empty installed = not matched)
        status = compute_client_status(round_, {}, {})
        assert status["weighted_score"] == 0
        assert status["color"] == "green"

    def test_behind_on_maintenance_is_yellow(self):
        """Client behind on several maintenance releases scores yellow."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name="BA GENERAL", releases=[
                    Release(sys_id="a", number="PR1",
                            short_description="BA GENERAL 8.27",
                            defects=[Defect(sys_id="d1", number="PD1", summary="fix")]),
                ]),
                UpgradeModule(name="BA HR", releases=[
                    Release(sys_id="b", number="PR2",
                            short_description="BA HR 8.34",
                            enhancements=[Enhancement(sys_id="e1", number="EN1", summary="feat")]),
                ]),
                UpgradeModule(name="BA POS CONT", releases=[
                    Release(sys_id="c", number="PR3",
                            short_description="BA POS CONT 9.3.30"),
                ]),
                UpgradeModule(name="BA FIN AID", releases=[
                    Release(sys_id="d", number="PR4",
                            short_description="BA FIN AID 9.3.57",
                            defects=[Defect(sys_id="d2", number="PD2", summary="fix2")]),
                ]),
                UpgradeModule(name="BA GENERAL CMN DB", releases=[
                    Release(sys_id="e", number="PR5",
                            short_description="BA GENERAL CMN DB 9.42"),
                ]),
                UpgradeModule(name="Banner Student", releases=[
                    Release(sys_id="f", number="PR6",
                            short_description="Banner Student 8.38",
                            defects=[Defect(sys_id="d3", number="PD3", summary="fix3")]),
                ]),
            ],
        )
        installed = {
            "BA GENERAL": "8.26", "BA HR": "8.33", "BA POS CONT": "9.3.29",
            "BA FIN AID": "9.3.56", "BA GENERAL CMN DB": "9.41",
            "Banner Student": "8.37",
        }
        status = compute_client_status(round_, installed, {})
        assert status["behind_count"] == 6
        assert status["color"] == "yellow"

    def test_regulatory_behind_weights_3x(self):
        """Regulatory releases behind count as 3x weight."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name="BA FIN AID", releases=[
                    Release(sys_id="a", number="PR1",
                            short_description="BA FIN AID 9.3.57",
                            release_purpose="regulatory",
                            enhancements=[Enhancement(sys_id="e1", number="EN1", summary="COD")]),
                ]),
            ],
        )
        installed = {"BA FIN AID": "9.3.56"}
        status = compute_client_status(round_, installed, {})
        assert status["weighted_score"] == 3
        assert status["modules_behind"][0]["weight"] == 3

    def test_security_behind_weights_2x(self):
        """Security/CVE releases behind count as 2x weight."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name="BA GEN BUS PROC API", releases=[
                    Release(sys_id="a", number="PR1",
                            short_description="BA GEN BUS PROC API 9.3.41.1",
                            defects=[Defect(sys_id="d1", number="PD1", summary="CVE-2025-66021")]),
                ]),
            ],
        )
        installed = {"BA GEN BUS PROC API": "9.3.40"}
        status = compute_client_status(round_, installed, {})
        assert status["weighted_score"] == 2
        assert status["modules_behind"][0]["weight"] == 2

    def test_client_page_link_in_details(self):
        """Client page link is included in status details."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name="BA FIN AID", releases=[
                    Release(sys_id="a", number="PR1",
                            short_description="BA FIN AID 9.3.57"),
                ]),
            ],
        )
        installed = {"BA FIN AID": "9.3.56"}
        client_link = "https://example.com/wiki/x/ABC"
        status = compute_client_status(round_, installed, {}, client_page_url=client_link)
        assert status["client_page_url"] == client_link

    def test_red_threshold(self):
        """High weighted score should be red."""
        round_ = UpgradeRound(
            title="Test", cutoff_date="2026-01-01",
            modules=[
                UpgradeModule(name=f"MOD{i}", releases=[
                    Release(sys_id=f"s{i}", number=f"PR{i}",
                            short_description=f"MOD{i} 2.0",
                            release_purpose="regulatory",
                            enhancements=[Enhancement(sys_id=f"e{i}", number=f"EN{i}", summary="reg")]),
                ])
                for i in range(5)
            ],
        )
        installed = {f"MOD{i}": "1.0" for i in range(5)}
        status = compute_client_status(round_, installed, {})
        # 5 regulatory modules * 3 = 15 weighted score → red
        assert status["weighted_score"] == 15
        assert status["color"] == "red"


class TestRenderStatusPage:
    def _make_statuses(self):
        return [
            {
                "client_name": "FHDA",
                "client_page_url": "https://example.com/fhda",
                "total_modules": 19,
                "behind_count": 2,
                "weighted_score": 4,
                "color": "green",
                "modules_behind": [
                    {"name": "BA FIN AID", "installed": "9.3.56", "latest": "9.3.57",
                     "type_label": "Enhancement/Regulatory", "weight": 3},
                    {"name": "BA GENERAL", "installed": "8.26", "latest": "8.27",
                     "type_label": "Defect", "weight": 1},
                ],
            },
            {
                "client_name": "IVC",
                "client_page_url": "https://example.com/ivc",
                "total_modules": 19,
                "behind_count": 8,
                "weighted_score": 12,
                "color": "yellow",
                "modules_behind": [],
            },
            {
                "client_name": "AVC",
                "client_page_url": "https://example.com/avc",
                "total_modules": 19,
                "behind_count": 15,
                "weighted_score": 20,
                "color": "red",
                "modules_behind": [],
            },
        ]

    def test_contains_table_structure(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert "<strong>Client</strong>" in html
        assert "<strong>Status</strong>" in html
        assert "<strong>Modules</strong>" in html
        assert "<strong>Behind</strong>" in html

    def test_contains_client_names_as_links(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert 'href="https://example.com/fhda"' in html
        assert ">FHDA</a>" in html

    def test_green_status_lozenge(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert 'ac:name="status"' in html
        assert 'ac:parameter ac:name="colour">Green' in html

    def test_yellow_status_lozenge(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert 'ac:parameter ac:name="colour">Yellow' in html

    def test_red_status_lozenge(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert 'ac:parameter ac:name="colour">Red' in html

    def test_expand_macro_for_behind_modules(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert 'ac:name="expand"' in html
        assert "BA FIN AID" in html
        assert "9.3.56" in html
        assert "9.3.57" in html

    def test_title_in_page(self):
        html = render_status_page(self._make_statuses(), "Spring 2026")
        assert "Spring 2026" in html
        assert "Upgrade Status" in html
