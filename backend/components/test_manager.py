
from wasabi import msg


import os
import asyncio
import json
import re
from urllib.parse import urlparse
from datetime import datetime



from backend.components.document import Document
from backend.components.interfaces import (
    Reader,
    Chunker,
    Embedding,
    Retriever,
    Generator,
)
from backend.server.helpers import LoggerManager
from backend.server.types import FileConfig, FileStatus, RAGComponentClass, RAGComponentConfig

# Import Readers
from backend.components.reader.BasicReader import BasicReader

# Import Chunkers

from backend.components.chunking.TokenChunker import TokenChunker
from backend.components.chunking.SentenceChunker import SentenceChunker
from backend.components.chunking.RecursiveChunker import RecursiveChunker
from backend.components.chunking.HTMLChunker import HTMLChunker
from backend.components.chunking.MarkdownChunker import MarkdownChunker
from backend.components.chunking.CodeChunker import CodeChunker
from backend.components.chunking.JSONChunker import JSONChunker
from backend.components.chunking.SemanticChunker import SemanticChunker



production = "Production"

if production != "Production":
    readers = [
        BasicReader(),

    ]
    chunkers = [
        TokenChunker(),
        SentenceChunker(),
        RecursiveChunker(),
        SemanticChunker(),
        HTMLChunker(),
        MarkdownChunker(),
        CodeChunker(),
        JSONChunker(),
    ]
    embedders = [

    ]
    retrievers = []
    generators = [

    ]
else:
    readers = [
        BasicReader(),

    ]
    chunkers = [
        TokenChunker(),
        SentenceChunker(),
        RecursiveChunker(),
        SemanticChunker(),
        HTMLChunker(),
        MarkdownChunker(),
        CodeChunker(),
        JSONChunker(),
    ]
    embedders = [

    ]
    retrievers = []
    generators = [

    ]


### ----------------------- ###


class ReaderManager:
    def __init__(self):
        self.readers: dict[str, Reader] = {reader.name: reader for reader in readers}

    async def load(
        self, reader: str, fileConfig: FileConfig, logger: LoggerManager
    ) -> list[Document]:
        try:
            loop = asyncio.get_running_loop()
            start_time = loop.time()
            if reader in self.readers:
                config = fileConfig.rag_config["Reader"].components[reader].config
                documents: list[Document] = await self.readers[reader].load(
                    config, fileConfig
                )
                for document in documents:
                    document.meta["Reader"] = (
                        fileConfig.rag_config["Reader"].components[reader].model_dump()
                    )
                elapsed_time = round(loop.time() - start_time, 2)
                if len(documents) == 1:
                    await logger.send_report(
                        fileConfig.fileID,
                        FileStatus.LOADING,
                        f"Loaded {fileConfig.filename}",
                        took=elapsed_time,
                    )
                else:
                    await logger.send_report(
                        fileConfig.fileID,
                        FileStatus.LOADING,
                        f"Loaded {fileConfig.filename} with {len(documents)} documents",
                        took=elapsed_time,
                    )
                await logger.send_report(
                    fileConfig.fileID, FileStatus.CHUNKING, "", took=0
                )
                return documents
            else:
                raise Exception(f"{reader} Reader not found")

        except Exception as e:
            raise Exception(f"Reader {reader} failed with: {str(e)}")



class ChunkerManager:
    def __init__(self):
        self.chunkers: dict[str, Chunker] = {
            chunker.name: chunker for chunker in chunkers
        }

    async def chunk(
        self,
        chunker: str,
        fileConfig: FileConfig,
        documents: list[Document],
        embedder: Embedding,
        logger: LoggerManager,
    ) -> list[Document]:
        try:
            loop = asyncio.get_running_loop()
            start_time = loop.time()
            if chunker in self.chunkers:
                config = fileConfig.rag_config["Chunker"].components[chunker].config
                embedder_config = (
                    fileConfig.rag_config["Embedder"].components[embedder.name].config
                )
                chunked_documents = await self.chunkers[chunker].chunk(
                    config=config,
                    documents=documents,
                    embedder=embedder,
                    embedder_config=embedder_config,
                )
                for chunked_document in chunked_documents:
                    chunked_document.meta["Chunker"] = (
                        fileConfig.rag_config["Chunker"]
                        .components[chunker]
                        .model_dump()
                    )
                elapsed_time = round(loop.time() - start_time, 2)
                if len(documents) == 1:
                    await logger.send_report(
                        fileConfig.fileID,
                        FileStatus.CHUNKING,
                        f"Split {fileConfig.filename} into {len(chunked_documents[0].chunks)} chunks",
                        took=elapsed_time,
                    )
                else:
                    await logger.send_report(
                        fileConfig.fileID,
                        FileStatus.CHUNKING,
                        f"Chunked all {len(chunked_documents)} documents with a total of {sum([len(document.chunks) for document in chunked_documents])} chunks",
                        took=elapsed_time,
                    )

                await logger.send_report(
                    fileConfig.fileID, FileStatus.EMBEDDING, "", took=0
                )
                return chunked_documents
            else:
                raise Exception(f"{chunker} Chunker not found")
        except Exception as e:
            raise e




file_config = FileConfig(
    fileID="file123",
    filename="test_file.txt",
    isURL=False,
    overwrite=True,
    extension="txt",
    source="local",
    content="",  # Set the Base64-encoded content here
    labels=["test", "mock"],
    rag_config={
        "Reader": RAGComponentClass(
            selected="BasicReader",
            components={
                "BasicReader": RAGComponentConfig(
                    name="BasicReader",
                    variables=[],
                    library=[],
                    description="A basic reader",
                    config={},
                    type="Reader",
                    available=True,
                )
            },
        ),
        "Chunker": RAGComponentClass(
            selected="TokenChunker",
            components={
                "TokenChunker": RAGComponentConfig(
                    name="TokenChunker",
                    variables=[],
                    library=[],
                    description="Splits text into tokens",
                    config={},
                    type="Chunker",
                    available=True,
                ),
                "SentenceChunker": RAGComponentConfig(
                    name="SentenceChunker",
                    variables=[],
                    library=[],
                    description="Splits text into sentences",
                    config={},
                    type="Chunker",
                    available=True,
                ),
            },
        ),
    },
    file_size=2000,  # Set the file size in bytes
    status=FileStatus.LOADING,  # Update file status as needed
    metadata="{}",
    status_report={},
)



import base64
file_config.content = base64.b64encode(file_config.content.encode('utf-8')).decode('utf-8')

print(file_config.content)

async def main():
    reader_manager = ReaderManager()
    logger = LoggerManager()
    documents = await reader_manager.load("BasicReader", file_config, logger)
    print("Loaded Documents:")
    for doc in documents:
        print(f"Content: {doc.content}, Meta: {doc.meta}")


asyncio.run(main())