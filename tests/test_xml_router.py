import asyncio

from src.bot.routers.tools import xml_tools


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def answer(self, text: str) -> None:  # pragma: no cover - exercised in tests
        self.replies.append(text)


SAMPLE_XML = "<library><book id=\"1\"><title>1984</title></book></library>"


def test_pretty_handler_formats_xml():
    message = DummyMessage(f"/xml_pretty {SAMPLE_XML}")
    asyncio.run(xml_tools.handle_pretty(message))
    assert message.replies
    assert message.replies[0].startswith("```xml")
    assert "<title>1984</title>" in message.replies[0]


def test_xpath_handler_attribute_selection():
    message = DummyMessage(f"/xml_xpath .//book/@id\n{SAMPLE_XML}")
    asyncio.run(xml_tools.handle_xpath(message))
    assert message.replies == ["1"]


def test_json_to_xml_handler_errors():
    message = DummyMessage("/json_to_xml not-json")
    asyncio.run(xml_tools.handle_json_to_xml(message))
    assert message.replies[0].startswith("Invalid JSON input")
