"""Firestore 초기 문서 적재 스크립트

seed_docs/*.txt 파일을 읽어 FirestoreVectorStore에 추가합니다.

실행 방법:
    export GEMINI_API_KEY=...
    python scripts/firestore_seed.py
"""
from __future__ import annotations

import glob
import os
import logging
from pathlib import Path

from langchain_google import GoogleGenerativeAIEmbeddings  # type: ignore

# 내부 서비스 모듈 import 경로 추가
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.firestore_vector import FirestoreVectorStore  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).resolve().parent / ".." / "seed_docs"


def main() -> None:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수가 설정되어 있지 않습니다.")

    embeddings = GoogleGenerativeAIEmbeddings(api_key=gemini_key)
    store = FirestoreVectorStore(embedding=embeddings)

    txt_files = glob.glob(str(SEED_DIR / "*.txt"))
    if not txt_files:
        logger.warning("seed_docs 디렉터리에 txt 파일이 없습니다. 스킵합니다.")
        return

    texts = []
    metadatas = []
    for path in txt_files:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        texts.append(text)
        metadatas.append({"filename": os.path.basename(path)})

    store.add_texts(texts, metadatas)
    logger.info("%d개의 문서를 Firestore에 업로드했습니다.", len(texts))


if __name__ == "__main__":
    main()
