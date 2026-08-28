from app.ingestion.youtube_parser import YoutubeParser


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
    