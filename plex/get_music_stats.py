import argparse
import logging
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import (
    datetime,
    timedelta,
)
from typing import Any

import progressbar

from plex.utils.get_sessions import (
    get_plex_session,
    get_tautulli_session,
)

progressbar.streams.wrap_stderr()
LOGGER = logging.getLogger()
hdlr = logging.StreamHandler()
LOGGER.addHandler(hdlr)
LOGGER.setLevel(logging.INFO)

# TODO: Memoize
# Not really useful on a yearly basis, but handy for testing

# TODO: Add as daily(?) maintenance task
# Don't have to worry about performance as much

# TODO: Think more about eliminating outliers

# TODO: Generate plots


def format_list_with_ties(
    sorted_plays: Iterable[tuple[str, float]],
    top_n: int = 5,
) -> tuple[str, ...]:
    out = []
    last_play_count = None
    current_place = 0
    cur_ties = []
    for item, count in sorted_plays:
        if count == last_play_count:
            cur_ties.append(item)
        else:
            if len(cur_ties) > 0:
                item_str = "; ".join(cur_ties)
                out.append(f"{current_place}. {item_str}: {count}")
            current_place += 1
            if current_place > top_n:
                break
            cur_ties = [item]

        last_play_count = count

    return tuple(out)


def get_top_with_ties(play_counts: Counter[str], top_n: int = 5) -> tuple[str, ...]:
    sorted_plays = play_counts.most_common()
    return format_list_with_ties(sorted_plays, top_n)


def get_top_normalized(
    play_counts: Counter[str],
    total_counts: Counter[str],
    top_n: int = 5,
) -> tuple[str, ...]:
    normed_counts = {}
    for item, count in play_counts.items():
        try:
            normed_counts[item] = round(count / total_counts[item], 2)
        except ZeroDivisionError:
            LOGGER.debug(f"Zero tracks for {item}")

    sorted_norms = sorted(normed_counts.items(), key=lambda item: item[1], reverse=True)
    return format_list_with_ties(sorted_norms, top_n)


def main(args: argparse.Namespace) -> None:
    plex_server = get_plex_session(api_key=args.plex_api_key, local=args.local, host=args.host)
    music_lib = plex_server.library.section(args.library_name)

    LOGGER.info("Getting map of all tracks to IDs + genre & style counts")
    all_tracks = {}
    album_counts: Counter[str] = Counter()
    artist_counts: Counter[str] = Counter()
    genre_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    total_artist_track_counts: Counter[str] = Counter()
    total_artist_album_counts: Counter[str] = Counter()
    for album in progressbar.progressbar(music_lib.albums()):
        artist = album.artist()
        if artist not in total_artist_track_counts:
            total_artist_track_counts[artist] = len(artist.tracks())
        if artist not in total_artist_album_counts:
            total_artist_album_counts[artist] = len(artist.albums())
        total_artist_tracks = total_artist_track_counts[artist]
        total_artist_albums = total_artist_album_counts[artist]

        tracks = {track.ratingKey: track for track in album.tracks()}
        all_tracks.update(tracks)

        track_count = len(tracks)

        album_formats = album.formats
        if len(album_formats) > 0 and album_formats[0].tag == "Album" and track_count > 1:
            full_album_name = f"{album.title} - {album.parentTitle}"
            album_counts[full_album_name] += track_count

        if (
            album.parentTitle != "Various Artists"
            and total_artist_tracks / total_artist_albums > 2  # TODO: Adjust this some more
        ):
            artist_counts[album.parentTitle] += track_count

        # TODO: Drop smallest X/Xth percentile?
        for genre in album.genres:
            genre_counts[genre.tag] += track_count

        for style in album.styles:
            style_counts[style.tag] += track_count

    now = datetime.now()

    year_ago = now - timedelta(days=365)

    tautulli_api = get_tautulli_session(args.tautulli_api_key, args.local, args.host)

    playtime_data = tautulli_api.get_library_watch_time_stats(music_lib.key, query_days=[365])[0]
    out_lines = [
        f"Minutes listened: {playtime_data['total_time'] // 60}",  # pylint: disable=invalid-sequence-index
        f"Tracks played: {playtime_data['total_plays']}\n",  # pylint: disable=invalid-sequence-index
    ]

    hist: dict[str, Any] = tautulli_api.get_history(
        user=args.user,
        after=year_ago,
        media_type="track",
        length=sys.maxsize,
        section_id=music_lib.key,
    )

    all_track_play_data = hist["data"]  # pylint: disable=invalid-sequence-index

    play_counts = Counter[str]()
    album_play_counts = Counter[str]()
    artist_play_counts = Counter[str]()
    genre_play_counts = Counter[str]()
    style_play_counts = Counter[str]()
    LOGGER.info("Collecting play count data")
    for track_play in progressbar.progressbar(all_track_play_data):
        # Skip plays that were not complete or are missing a title, for some reason
        if track_play["watched_status"] == 1 and track_play["title"] != "":
            track_id = int(track_play["rating_key"])
            lib_item = all_tracks.get(track_id)
            if lib_item is None:
                LOGGER.warning(
                    f"{track_play['full_title'] + ' - ' + track_play['grandparent_title']} (id = {track_id}) not found"
                )
                track_play["full_title"] = (
                    f"{track_play['title']} - {track_play['grandparent_title']}"
                )
                track_play["full_parent_title"] = (
                    f"{track_play['parent_title']} - {track_play['grandparent_title']}"
                )
            else:
                track_play["full_title"] = f"{lib_item.title} - {lib_item.grandparentTitle}"
                track_play["full_parent_title"] = (
                    f"{lib_item.parentTitle} - {lib_item.grandparentTitle}"
                )

            play_counts[track_play["full_title"]] += 1
            album_play_counts[track_play["full_parent_title"]] += 1

            if track_play["grandparent_title"] != "Various Artists":
                artist_play_counts[track_play["grandparent_title"]] += 1
            else:
                artist_play_counts[track_play["original_title"]] += 1

            if lib_item is not None:
                for genre in lib_item.album().genres:
                    genre_play_counts[genre.tag] += 1
                for style in lib_item.album().styles:
                    style_play_counts[style.tag] += 1

    # TODO: Clean this up
    out_lines.append("Top 5 tracks, including ties:")
    out_lines.extend(get_top_with_ties(play_counts))
    out_lines.append("")

    out_lines.append("Top 5 albums, including ties:")
    out_lines.extend(get_top_with_ties(album_play_counts))
    out_lines.append("")

    out_lines.append("Top 5 artists, including ties:")
    out_lines.extend(get_top_with_ties(artist_play_counts))
    out_lines.append("")

    out_lines.append("Top 5 styles, including ties:")
    out_lines.extend(get_top_with_ties(style_play_counts))
    out_lines.append("")

    out_lines.append("Top 5 genres, including ties:")
    out_lines.extend(get_top_with_ties(genre_play_counts))
    out_lines.append("")

    out_lines.append("Top 5 albums, normalized, including ties:")
    out_lines.extend(get_top_normalized(album_play_counts, album_counts))
    out_lines.append("")

    out_lines.append("Top 5 artists, normalized, including ties:")
    out_lines.extend(get_top_normalized(artist_play_counts, artist_counts))
    out_lines.append("")

    out_lines.append("Top 5 styles, normalized, including ties:")
    out_lines.extend(get_top_normalized(style_play_counts, style_counts))
    out_lines.append("")

    out_lines.append("Top 5 genres, normalized, including ties:")
    out_lines.extend(get_top_normalized(genre_play_counts, genre_counts))
    out_lines.append("")

    LOGGER.info("\n".join(out_lines))


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("user", type=str)
    parser.add_argument("plex_api_key", type=str)
    parser.add_argument("tautulli_api_key", type=str)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--library-name", type=str, default="Music")
    parser.add_argument("--host", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    main(cli())
