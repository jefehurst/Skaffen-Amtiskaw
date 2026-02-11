"""Tests for upgrade.py — grouping, filtering, module name parsing."""

import json

import pytest

from ellucian_support.release import Release
from ellucian_support.upgrade import (
    ESM_TO_MODULE,
    MODULE_TO_ESM,
    UpgradeModule,
    UpgradeRound,
    _group_releases,
    match_installed_versions,
    parse_module_name,
    should_exclude,
)


class TestParseModuleName:
    def test_simple_version(self):
        assert parse_module_name("BA FIN AID 9.3.57") == "BA FIN AID"

    def test_multi_part_version(self):
        assert parse_module_name("BA GENERAL CMN DB 9.41") == "BA GENERAL CMN DB"

    def test_dotted_version(self):
        assert parse_module_name("BA Student TCC 9.3.41.1") == "BA Student TCC"

    def test_banner_prefix(self):
        assert parse_module_name("Banner Event Publisher 9.21") == "Banner Event Publisher"

    def test_two_part_name(self):
        assert parse_module_name("BA CALBHR 8.28") == "BA CALBHR"

    def test_single_digit_version(self):
        assert parse_module_name("BA NPYRE 9.3.38") == "BA NPYRE"

    def test_no_version(self):
        assert parse_module_name("BA FIN AID") == "BA FIN AID"

    def test_empty_string(self):
        assert parse_module_name("") == ""

    def test_version_only(self):
        # Edge case: all tokens look like version numbers
        assert parse_module_name("9.3.57") == "9.3.57"

    def test_tax_update(self):
        assert parse_module_name("BA HR Tax Update #346") == "BA HR Tax Update"

    def test_tax_update_low_number(self):
        assert parse_module_name("BA HR Tax Update #339") == "BA HR Tax Update"

    def test_repost_suffix(self):
        assert parse_module_name("BA FIN AID 8.55 - REPOST") == "BA FIN AID"


class TestShouldExclude:
    def test_excludes_saas(self):
        assert should_exclude("Banner SaaS Voyager 2026.1") is True

    def test_excludes_europe(self):
        assert should_exclude("BA STUDENT EUROPE HESA 9.3") is True

    def test_excludes_australia(self):
        assert should_exclude("ASCGEN Australia 9.1") is True

    def test_excludes_texas(self):
        assert should_exclude("BA Texas 1098T 9.2") is True

    def test_excludes_uk(self):
        assert should_exclude("SC UK Something 1.0") is True

    def test_case_insensitive(self):
        assert should_exclude("Banner SAAS Something 1.0") is True

    def test_allows_normal_release(self):
        assert should_exclude("BA FIN AID 9.3.57") is False

    def test_allows_general(self):
        assert should_exclude("BA GENERAL 8.26") is False

    def test_excludes_tcc(self):
        assert should_exclude("BA Student TCC 9.3.41") is True

    def test_excludes_npyre(self):
        assert should_exclude("BA NPYRE 8.17") is True

    def test_excludes_structured_progression(self):
        assert should_exclude("Structured Progression 2.2") is True

    def test_excludes_bdr(self):
        assert should_exclude("BDR DR 8.6") is True

    def test_excludes_tric(self):
        assert should_exclude("BA TRIC 9.3.39") is True

    def test_excludes_canada(self):
        assert should_exclude("SC Canada T2202 8.25.1") is True

    def test_excludes_canadian(self):
        assert should_exclude("BA HR TD1 Tax Update 030, Canadian Customers") is True

    def test_excludes_banner_in_experience(self):
        assert should_exclude("Banner in Experience - v4.3.2") is True

    def test_excludes_print_app(self):
        assert should_exclude("BA GEN PRINT APP 9.8") is True

    def test_allows_tax_update(self):
        assert should_exclude("BA HR Tax Update #346") is False


class TestGroupReleases:
    def _make_release(self, short_desc, target_ga="", date_released=""):
        return Release(
            sys_id=f"id_{short_desc}",
            number=f"PR_{short_desc}",
            short_description=short_desc,
            target_ga_date=target_ga,
            date_released=date_released,
        )

    def test_groups_by_module(self):
        releases = [
            self._make_release("BA FIN AID 9.3.57", target_ga="2026-03-19"),
            self._make_release("BA FIN AID 8.56", target_ga="2026-03-19"),
            self._make_release("BA GENERAL 8.26", target_ga="2026-03-19"),
        ]
        modules = _group_releases(releases)
        assert len(modules) == 2
        assert modules[0].name == "BA FIN AID"
        assert len(modules[0].releases) == 2
        assert modules[1].name == "BA GENERAL"
        assert len(modules[1].releases) == 1

    def test_preserves_encounter_order(self):
        releases = [
            self._make_release("BA STUDENT 8.37", target_ga="2026-03-19"),
            self._make_release("BA FIN AID 9.3.57", target_ga="2026-03-19"),
            self._make_release("BA STUDENT 9.3.40", target_ga="2026-03-19"),
        ]
        modules = _group_releases(releases)
        assert modules[0].name == "BA STUDENT"
        assert modules[1].name == "BA FIN AID"

    def test_sorts_releases_by_date(self):
        releases = [
            self._make_release("BA FIN AID 9.3.57", target_ga="2026-03-19"),
            self._make_release("BA FIN AID 8.56", target_ga="2026-02-15"),
        ]
        modules = _group_releases(releases)
        # Earlier date should come first
        assert modules[0].releases[0].short_description == "BA FIN AID 8.56"
        assert modules[0].releases[1].short_description == "BA FIN AID 9.3.57"

    def test_groups_tax_updates(self):
        releases = [
            self._make_release("BA HR Tax Update #346"),
            self._make_release("BA HR Tax Update #339"),
            self._make_release("BA HR Tax Update #342"),
        ]
        modules = _group_releases(releases)
        assert len(modules) == 1
        assert modules[0].name == "BA HR Tax Update"
        # Should be sorted by update number
        descs = [r.short_description for r in modules[0].releases]
        assert descs == [
            "BA HR Tax Update #339",
            "BA HR Tax Update #342",
            "BA HR Tax Update #346",
        ]

    def test_repost_groups_with_module(self):
        releases = [
            self._make_release("BA FIN AID 9.3.57", target_ga="2026-03-19"),
            self._make_release("BA FIN AID 8.55 - REPOST", target_ga="2026-01-15"),
        ]
        modules = _group_releases(releases)
        assert len(modules) == 1
        assert modules[0].name == "BA FIN AID"
        assert len(modules[0].releases) == 2

    def test_empty_input(self):
        assert _group_releases([]) == []


class TestUpgradeRoundSerialization:
    def test_to_dict_and_back(self):
        round_ = UpgradeRound(
            title="Spring 2026",
            cutoff_date="2026-03-19",
            since_date="2025-12-12",
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
                        )
                    ],
                ),
            ],
        )

        json_str = round_.to_json()
        restored = UpgradeRound.from_json(json_str)

        assert restored.title == "Spring 2026"
        assert restored.cutoff_date == "2026-03-19"
        assert len(restored.modules) == 1
        assert restored.modules[0].name == "BA FIN AID"
        assert len(restored.modules[0].releases) == 1
        assert restored.modules[0].releases[0].prerequisites == ["BA GENERAL 8.25"]

    def test_json_is_valid(self):
        round_ = UpgradeRound(title="Test", cutoff_date="2026-01-01")
        parsed = json.loads(round_.to_json())
        assert parsed["title"] == "Test"
        assert parsed["modules"] == []


class TestEsmToModuleMapping:
    def test_mapping_is_bidirectional(self):
        """Every key in ESM_TO_MODULE should have a reverse in MODULE_TO_ESM."""
        for esm_name, module_name in ESM_TO_MODULE.items():
            assert MODULE_TO_ESM[module_name] == esm_name

    def test_reverse_mapping_is_bidirectional(self):
        """Every key in MODULE_TO_ESM should have a reverse in ESM_TO_MODULE."""
        for module_name, esm_name in MODULE_TO_ESM.items():
            assert ESM_TO_MODULE[esm_name] == module_name

    def test_known_mappings(self):
        assert ESM_TO_MODULE["General DB"] == "BA GENERAL CMN DB"
        assert ESM_TO_MODULE["Financial Aid"] == "BA FIN AID"
        assert ESM_TO_MODULE["Finance"] == "BA FINANCE"
        assert ESM_TO_MODULE["Student"] == "Banner Student"
        assert ESM_TO_MODULE["General"] == "BA GENERAL"

    def test_reverse_known_mappings(self):
        assert MODULE_TO_ESM["BA GENERAL CMN DB"] == "General DB"
        assert MODULE_TO_ESM["BA FIN AID"] == "Financial Aid"
        assert MODULE_TO_ESM["BA FINANCE"] == "Finance"

    def test_no_duplicate_values(self):
        """Each ServiceNow module name should map to exactly one ESM name."""
        module_names = list(ESM_TO_MODULE.values())
        assert len(module_names) == len(set(module_names))


class TestMatchInstalledVersions:
    def _make_round(self):
        return UpgradeRound(
            title="Spring 2026",
            cutoff_date="2026-03-19",
            modules=[
                UpgradeModule(
                    name="BA FIN AID",
                    releases=[
                        Release(sys_id="a", number="PR1", short_description="BA FIN AID 9.3.57"),
                    ],
                ),
                UpgradeModule(
                    name="BA GENERAL CMN DB",
                    releases=[
                        Release(sys_id="b", number="PR2", short_description="BA GENERAL CMN DB 9.41"),
                    ],
                ),
                UpgradeModule(
                    name="BA FINANCE",
                    releases=[
                        Release(sys_id="c", number="PR3", short_description="BA FINANCE 9.14"),
                    ],
                ),
            ],
        )

    def test_matches_esm_names_to_modules(self):
        esm_versions = {
            "Financial Aid": "9.3.56",
            "General DB": "9.40",
            "Finance": "9.13",
        }
        result = match_installed_versions(esm_versions, self._make_round())
        assert result == {
            "BA FIN AID": "9.3.56",
            "BA GENERAL CMN DB": "9.40",
            "BA FINANCE": "9.13",
        }

    def test_only_includes_modules_in_round(self):
        esm_versions = {
            "Financial Aid": "9.3.56",
            "General DB": "9.40",
            "Finance": "9.13",
            "HR": "9.10",  # Not in the round
        }
        result = match_installed_versions(esm_versions, self._make_round())
        assert "BA HR" not in result
        assert len(result) == 3

    def test_skips_unmatched_esm_products(self):
        esm_versions = {
            "Some Unknown Product": "1.0",
        }
        result = match_installed_versions(esm_versions, self._make_round())
        assert result == {}

    def test_empty_esm_versions(self):
        result = match_installed_versions({}, self._make_round())
        assert result == {}

    def test_partial_match(self):
        """Only some ESM products match modules in the round."""
        esm_versions = {
            "Financial Aid": "9.3.56",
        }
        result = match_installed_versions(esm_versions, self._make_round())
        assert result == {"BA FIN AID": "9.3.56"}
        assert len(result) == 1
