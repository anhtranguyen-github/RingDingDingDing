from backend.components.reader.BasicReader import BasicReader
from backend.server.types import FileConfig
import asyncio
import base64

# Example usage
async def run_reader_example():
    # Create a FileConfig object for a sample text file
    sample_text = "This is a sample text file content."
    encoded_text = base64.b64encode(sample_text.encode("utf-8")).decode("utf-8")
    file_config = FileConfig(
        fileID="12345",
        filename="sample.txt",
        isURL=False,
        overwrite=False,
        extension=".txt",
        source="local",
        content=encoded_text,
        labels=[],
        rag_config={},
        file_size=len(sample_text),
        status="READY",
        metadata="{}",
        status_report={},
    )

    # Initialize the BasicReader
    reader = BasicReader()

    # Load and process the file
    documents = await reader.load({}, file_config)

    # Print the results
    for doc in documents:
        print(f"Document content: {doc.content}")
        print(f"Metadata: {doc.metadata}")
        print()



asyncio.run(run_reader_example())