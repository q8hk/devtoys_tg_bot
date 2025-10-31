from src.bot import keyboards
from src.bot.commands import (
    COMMAND_SPECS,
    default_scope_command_specs,
    group_scope_command_specs,
    private_scope_command_specs,
    section_commands,
)


def test_private_scope_includes_all_menu_commands() -> None:
    private_names = {spec.name for spec in private_scope_command_specs()}
    for spec in COMMAND_SPECS:
        if spec.show_in_menu:
            assert spec.name in private_names


def test_default_scope_subset_of_private_scope() -> None:
    private_names = {spec.name for spec in private_scope_command_specs()}
    default_names = {spec.name for spec in default_scope_command_specs()}
    assert default_names.issubset(private_names)


def test_group_scope_matches_default_scope() -> None:
    group_names = {spec.name for spec in group_scope_command_specs()}
    default_names = {spec.name for spec in default_scope_command_specs()}
    assert group_names == default_names


def test_each_home_section_has_guide_commands() -> None:
    for section, _ in keyboards.HOME_SECTIONS:
        commands = section_commands(section, for_guide=True)
        assert commands, f"Expected guide commands for section {section}"
