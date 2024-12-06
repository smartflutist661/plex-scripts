from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import (
    Callable,
    Mapping,
)
from functools import partial
from typing import cast

from plexapi.audio import Audio
from plexapi.exceptions import NotFound
from plexapi.photo import Photo
from plexapi.video import Video

from plex.utils.get_sessions import get_plex_session

Sortable = str | float | int | bool

PLAYLIST_ORDERS: Mapping[tuple[str, ...], tuple[str, ...]] = {
    # These should be 100% rated
    ("ARTIST", "RATING"): (
        "Love Songs",
        "Openings",
        "Running",
        "Singing",
        "Workout",
    ),
    ("RATING",): ("Played",),
}

SORT_TITLE_PATTERN = re.compile("^the |^a |^an ")


def get_item_artist(item: Video | Audio | Photo) -> str:
    return str(item.artist().titleSort.lower())


def get_item_album(item: Video | Audio | Photo) -> str:
    return str(item.album().titleSort.lower())


def get_item_rating(item: Video | Audio | Photo) -> float:
    return float(-item.userRating if item.userRating is not None else 1)


SORT_FUNCS: Mapping[str, Callable[[Video | Audio | Photo], Sortable]] = {
    "ARTIST": get_item_artist,
    "ALBUM": get_item_album,
    "RATING": get_item_rating,
}


def get_item_sort(
    item: Video | Audio | Photo,
    sort_order: tuple[str, ...],
) -> tuple[Sortable, ...]:
    return tuple(SORT_FUNCS[sort_level](item) for sort_level in sort_order)


def main(args: argparse.Namespace) -> None:
    if args.v is True:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    else:
        logging.basicConfig(level=logging.WARNING, stream=sys.stdout)

    plex_server = get_plex_session(args.api_key, args.local, args.host)

    for playlist_sort, playlist_names in PLAYLIST_ORDERS.items():
        for playlist_name in playlist_names:
            logging.info(f"Sorting {playlist_name}")
            try:
                playlist = plex_server.playlist(playlist_name)
            except NotFound:
                logging.error(f"{playlist_name} not found, skipping.")

            playlist_items = playlist.items()
            # Some type inference is wrong here after the sort,
            # since it should be idempotent, type-wise
            playlist_items = cast(
                list[Video] | list[Audio] | list[Photo],
                sorted(playlist_items, key=partial(get_item_sort, sort_order=playlist_sort)),
            )

            playlist.delete()
            plex_server.createPlaylist(
                title=playlist_name,
                items=playlist_items,
            )


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sort playlists.")
    parser.add_argument("api_key", type=str)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("-v", action="store_true")
    parser.add_argument("--host", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    main(cli())
