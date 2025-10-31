"""Handlers exposing XML tools through aiogram routers."""

from __future__ import annotations

from xml.etree.ElementTree import ParseError

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.utils.xml_ import json_to_xml, minify_xml, pretty_xml, xml_to_json, xpath_query

router = Router(name="xml_tools")

__all__ = ["router"]


_XML_REQUIRED = "Send XML payload after the command."
_JSON_REQUIRED = "Send JSON payload after the command."
_XPATH_REQUIRED = "Provide the XPath expression on the first line followed by XML." \
    " Separate them with a newline."


def _extract_payload(message: Message) -> str:
    text = message.text or ""
    _, _, payload = text.partition(" ")
    return payload.strip()


def _wrap_block(content: str, language: str) -> str:
    return f"```{language}\n{content}\n```"


@router.message(Command("xml_pretty"))
async def handle_pretty(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(_XML_REQUIRED)
        return

    try:
        formatted = pretty_xml(payload)
    except ParseError:
        await message.answer("Invalid XML input.")
        return

    await message.answer(_wrap_block(formatted, "xml"))


@router.message(Command("xml_minify"))
async def handle_minify(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(_XML_REQUIRED)
        return

    try:
        compact = minify_xml(payload)
    except ParseError:
        await message.answer("Invalid XML input.")
        return

    await message.answer(_wrap_block(compact, "xml"))


@router.message(Command("xml_to_json"))
async def handle_xml_to_json(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(_XML_REQUIRED)
        return

    try:
        converted = xml_to_json(payload)
    except ParseError:
        await message.answer("Invalid XML input.")
        return

    await message.answer(_wrap_block(converted, "json"))


@router.message(Command("json_to_xml"))
async def handle_json_to_xml(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(_JSON_REQUIRED)
        return

    try:
        converted = json_to_xml(payload, pretty=True)
    except ValueError as exc:
        await message.answer(f"Invalid JSON input: {exc}")
        return

    await message.answer(_wrap_block(converted, "xml"))


@router.message(Command("xml_xpath"))
async def handle_xpath(message: Message) -> None:
    payload = _extract_payload(message)
    if not payload:
        await message.answer(_XPATH_REQUIRED)
        return

    if "\n" not in payload:
        await message.answer(_XPATH_REQUIRED)
        return

    expression, xml_input = payload.split("\n", 1)
    expression = expression.strip()
    xml_input = xml_input.strip()
    if not expression or not xml_input:
        await message.answer(_XPATH_REQUIRED)
        return

    try:
        matches = xpath_query(xml_input, expression)
    except ParseError:
        await message.answer("Invalid XML input.")
        return
    except ValueError as exc:
        await message.answer(f"Unsupported XPath expression: {exc}")
        return

    if not matches:
        await message.answer("No matches found.")
        return

    if expression.endswith("/text()"):
        await message.answer("\n".join(matches))
        return
    if "/@" in expression:
        await message.answer("\n".join(matches))
        return

    await message.answer(_wrap_block("\n\n".join(matches), "xml"))
