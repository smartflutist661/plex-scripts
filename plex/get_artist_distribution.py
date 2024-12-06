import argparse
import json
from collections import Counter

from matplotlib import pyplot as plt

from plex.utils.get_sessions import get_plex_session


def main(args: argparse.Namespace) -> None:
    plex_server = get_plex_session(args.api_key, args.local, args.host)

    music_lib = plex_server.library.section(args.library_name)
    track_counts = Counter(
        {
            artist.title: len(artist.tracks())
            for artist in music_lib.recentlyAddedArtists(maxresults=5000)
        }
    )

    sorted_artists = track_counts.most_common()
    top_artists = sorted_artists[:10]
    bottom_artists = [track_count for track_count in sorted_artists if track_count[1] < 10]
    print(json.dumps(top_artists, indent=2))
    print(json.dumps(bottom_artists, indent=2))

    plt.hist(
        list(track_counts.values()),
        bins=list(range(0, 60, 10))
        + list(range(50, 225, 25))
        + list(range(200, 550, 50))
        + list(range(500, top_artists[0][1] + 100, 100)),
    )
    plt.show()


def cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_key", type=str)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--library-name", type=str, default="Music")
    parser.add_argument("--host", type=str, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    main(cli())
