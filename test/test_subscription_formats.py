from app.ingestion.youtube_parser import YoutubeParser
from app.ingestion.dispatcher import Dispatcher


def test_find_csv_subscriptions(tmp_path):
    subscriptions = tmp_path / "subscriptions.csv"
    subscriptions.write_text(
        "Channel Id,Channel Url,Channel Title\n"
        "UC123,https://www.youtube.com/channel/UC123,Example Channel\n",
        encoding="utf-8",
    )

    dispatcher = Dispatcher()

    result = dispatcher._find_subscriptions(tmp_path)

    assert result == subscriptions


def test_find_tsv_subscriptions(tmp_path):
    subscriptions = tmp_path / "subscriptions.tsv"
    subscriptions.write_text(
        "Channel Id\tChannel Url\tChannel Title\n"
        "UC123\thttps://www.youtube.com/channel/UC123\tExample Channel\n",
        encoding="utf-8",
    )

    dispatcher = Dispatcher()

    result = dispatcher._find_subscriptions(tmp_path)

    assert result == subscriptions


def test_parse_csv_subscriptions(tmp_path):
    subscriptions = tmp_path / "subscriptions.csv"
    subscriptions.write_text(
        "Channel Id,Channel Url,Channel Title\n"
        "UC123,https://www.youtube.com/channel/UC123,Example Channel\n",
        encoding="utf-8",
    )

    parser = YoutubeParser(
        watch_history_path="unused.json",
        subscriptions_path=str(subscriptions),
    )

    result = parser.parse_subscriptions()

    assert len(result) == 1
    assert result[0].channel_id == "UC123"
    assert result[0].channel_url == "https://www.youtube.com/channel/UC123"
    assert result[0].channel_title == "Example Channel"


def test_parse_tsv_subscriptions(tmp_path):
    subscriptions = tmp_path / "subscriptions.tsv"
    subscriptions.write_text(
        "Channel Id\tChannel Url\tChannel Title\n"
        "UC123\thttps://www.youtube.com/channel/UC123\tExample Channel\n",
        encoding="utf-8",
    )

    parser = YoutubeParser(
        watch_history_path="unused.json",
        subscriptions_path=str(subscriptions),
    )

    result = parser.parse_subscriptions()

    assert len(result) == 1
    assert result[0].channel_id == "UC123"
    assert result[0].channel_url == "https://www.youtube.com/channel/UC123"
    assert result[0].channel_title == "Example Channel"

def test_find_xls_subscriptions_does_not_text_scan_binary_file(
    tmp_path, monkeypatch
):
    subscriptions = tmp_path / "subscriptions.xls"
    subscriptions.write_bytes(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1binary-excel-data"
    )

    dispatcher = Dispatcher()

    original_open = open
    text_scan_attempted = False

    def guarded_open(file, *args, **kwargs):
        nonlocal text_scan_attempted

        if str(file).endswith(".xls") and (
            not args or "b" not in str(args[0])
        ):
            text_scan_attempted = True

        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", guarded_open)

    dispatcher._find_subscriptions(tmp_path)

    assert not text_scan_attempted

def test_find_xls_subscriptions_from_workbook(tmp_path, monkeypatch):
    subscriptions = tmp_path / "subscriptions.xls"
    subscriptions.write_bytes(b"fake-xls")

    class FakeSheet:
        nrows = 2

        def row_values(self, row_idx):
            rows = [
                ["Channel Id", "Channel Url", "Channel Title"],
                [
                    "UC123",
                    "https://www.youtube.com/channel/UC123",
                    "Example Channel",
                ],
            ]
            return rows[row_idx]

    class FakeWorkbook:
        def sheet_by_index(self, index):
            assert index == 0
            return FakeSheet()

    monkeypatch.setattr(
        "app.ingestion.dispatcher.xlrd.open_workbook",
        lambda *args, **kwargs: FakeWorkbook(),
    )

    dispatcher = Dispatcher()

    result = dispatcher._find_subscriptions(tmp_path)

    assert result == subscriptions
    