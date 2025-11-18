# app/services/base.py

import re
import os
import shutil
from fastapi import Request
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import Docx2txtLoader
from app.config import settings
import aiofiles

class Base:
    """
    Класс для работы с базой знаний.
    Поддерживает загрузку исходного документа, разбиение на чанки,
    построение FAISS-индекса и его сохранение/чтение с диска.
    """

    def __init__(self):
        self.log = None  # будет присвоен из request.app.state.log при использовании
        # Пути из settings (.env)
        self.local_path = settings.BASE_LOCAL_PATH
        self.index_path = settings.BASE_LOCAL_INDEX
        # Внутреннее состояние
        self.chunks = []
        self.index = None
        self.embeddings = OpenAIEmbeddings()
        # Загружаем индекс
        self.load_index()

    def attach_request(self, request: Request):
        """Присоединяет request для логирования и обновления app.state.base при rebuild."""
        self.log = request.app.state.log
        self.request = request

    # ==========================================================
    # ЧТЕНИЕ ДОКУМЕНТА
    # ==========================================================
    def load_local_document(self) -> str:
        """Загружает локальный документ и возвращает его текст (.docx или .txt)."""
        if not os.path.exists(self.local_path):
            raise FileNotFoundError(f"Файл не найден: {self.local_path}")

        if self.local_path.endswith(".docx"):
            loader = Docx2txtLoader(self.local_path)
            docs = loader.load()
            return " ".join([doc.page_content for doc in docs])
        else:
            with open(self.local_path, "r", encoding="utf-8") as f:
                return f.read()

    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    @staticmethod
    def duplicate_headers_without_hashes(text: str) -> str:
        """Дублирует заголовки документа без символа `#`."""
        def replacer(match):
            return match.group() + "\n" + match.group().replace("#", "").strip()
        return re.sub(r"#{1,2} .+", replacer, text)

    @staticmethod
    def split_document_into_chunks(text: str):
        """Разбивает документ на чанки по заголовкам."""
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        return splitter.split_text(text)

    # ==========================================================
    # РАБОТА С ИНДЕКСОМ
    # ==========================================================
    def build_index(self):
        """Строит FAISS-индекс из исходного документа и сохраняет в память."""
        text = self.load_local_document()
        text = self.duplicate_headers_without_hashes(text)
        self.chunks = self.split_document_into_chunks(text)
        self.index = FAISS.from_documents(self.chunks, self.embeddings)
        return self.index

    def save_index(self):
        """Сохраняет FAISS-индекс локально в папку index_path."""
        if self.index is None:
            raise ValueError("Индекс ещё не создан. Сначала вызови build_index().")

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self.index.save_local(self.index_path)

    def load_index(self):
        """Загружает FAISS-индекс из локальной папки или создаёт новый."""
        if os.path.exists(self.index_path):
            self.index = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            self.build_index()
            self.save_index()
        return self.index

    async def rebuild_index(self, request: Request = None):
        """Пересоздаёт FAISS-индекс и обновляет глобальный объект app.state.base, если request передан."""
        if request:
            self.attach_request(request)

        if self.log:
            await self.log.log_info("base", "Пересоздание FAISS индекса начато")

        if os.path.exists(self.index_path):
            shutil.rmtree(self.index_path, ignore_errors=True)

        self.build_index()
        self.save_index()

        # обновляем глобальный объект
        if request:
            request.app.state.base = self

        if self.log:
            await self.log.log_info("base", "FAISS индекс пересоздан", {"index_path": self.index_path})
        return True

    async def search_chunks(self, query: str, k: int = 5):
        """Выполняет поиск по индексной базе и возвращает список релевантных чанков."""
        if self.index is None:
            self.load_index()

        results = self.index.similarity_search_with_score(query, k=k)

        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })

        formatted_results.sort(key=lambda x: x["score"])  # чем меньше score, тем релевантнее

        if self.log:
            await self.log.log_info("base_search", "Поиск по FAISS", {
                "query": query,
                "results_count": len(formatted_results)
            })

        return formatted_results

    # ======================
    # ЧТЕНИЕ/СОХРАНЕНИЕ FAQ
    # ======================
    async def base_read(self) -> str:
        """Асинхронно читает содержимое файла 'base/faq.md' и возвращает текст."""
        path = os.path.join("base", "faq.md")
        if not os.path.exists(path):
            if self.log:
                await self.log.log_warning("base_read", f"Файл не найден: {path}")
            return ""
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            return await f.read()

    async def base_save(self, text: str):
        """Асинхронно сохраняет текст в файл 'base/faq.md'."""
        os.makedirs("base", exist_ok=True)
        async with aiofiles.open(os.path.join("base", "faq.md"), mode="w", encoding="utf-8") as f:
            await f.write(text)
        if self.log:
            await self.log.log_info("base_save", "Файл FAQ сохранен")