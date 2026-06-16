import argparse
import re
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable

VIDEO_ID_RE = re.compile(
    r"(?:v=|\/embed\/|\/v\/|youtu\.be\/|\/shorts\/)([a-zA-Z0-9_-]{11})"
)

def extract_video_id(url_or_id: str) -> str:
    """Extract a YouTube video ID from a full URL or return the ID directly."""
    match = VIDEO_ID_RE.search(url_or_id)
    if match:
        return match.group(1)
    if len(url_or_id) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url_or_id):
        return url_or_id
    raise ValueError("Geçerli bir YouTube video URL'si veya video ID'si girin.")


def download_transcript(video_id: str, language: str | None = None):
    """Download transcript data for the given video ID."""
    client = YouTubeTranscriptApi()
    transcript_list = client.list(video_id)

    if language:
        transcript = transcript_list.find_transcript([language])
    else:
        transcript = next(iter(transcript_list))

    return transcript.fetch()


def format_transcript(transcript) -> str:
    """Convert transcript blocks into readable text."""
    lines = []
    for item in transcript:
        if isinstance(item, dict):
            text = item.get("text", "")
        else:
            text = getattr(item, "text", None)
            if text is None and isinstance(item, str):
                text = item
        if text:
            lines.append(text)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YouTube videosu için transcript çıkarır ve bir .txt dosyasına kaydeder."
    )
    parser.add_argument(
        "video",
        help="YouTube video URL'si veya video ID'si",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="İstenen transcript dili (örnek: en, tr)",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Çıktı dosyası adı (varsayılan: <video_id>_transcript.txt)",
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        video_id = extract_video_id(args.video)
    except ValueError as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output or f"{video_id}_transcript.txt")

    try:
        transcript = download_transcript(video_id, args.language)
    except NoTranscriptFound:
        print("Transcript bulunamadı. Video için transcript mevcut olmayabilir.", file=sys.stderr)
        return 2
    except TranscriptsDisabled:
        print("Transcript özelliği bu video için devre dışı bırakılmış.", file=sys.stderr)
        return 3
    except VideoUnavailable:
        print("Video bulunamadı veya erişilemiyor.", file=sys.stderr)
        return 4
    except Exception as exc:
        if "ssl" in str(exc).lower() or "network" in str(exc).lower() or "connection" in str(exc).lower():
            print("Ağ bağlantısı hatası. İnternet bağlantınızı kontrol edin veya daha sonra tekrar deneyin.", file=sys.stderr)
            return 6
        print(f"Beklenmeyen bir hata oluştu: {exc}", file=sys.stderr)
        return 5

    text = format_transcript(transcript)
    output_path.write_text(text, encoding="utf-8")

    print(f"Transcript başarıyla kaydedildi: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
