from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from pathlib import Path
from models import ProcessingEnum
from chunking import semantic_chunker as chunker_module
from extraction.merged_pipeline import run_merged_pipeline

class CustomDocument:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1].lower()

    def get_file_content(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading text file: {e}")
                return None

        if file_ext == ProcessingEnum.PDF.value:
            # Create a separate output directory for this project
            output_dir = os.path.join(self.project_path, "output")
            os.makedirs(output_dir, exist_ok=True)

            try:
                # Run local advanced merged pipeline
                run_merged_pipeline(
                    source=file_path,
                    output_dir=Path(output_dir),
                    vision_model=self.app_settings.GENERATION_MODEL_ID or "minicpm-v",
                    text_model="phi3:mini",
                )

                # The output markdown is saved under the same file stem name
                stem = Path(file_id).stem
                md_path = os.path.join(output_dir, f"{stem}.md")
                
                if os.path.exists(md_path):
                    with open(md_path, "r", encoding="utf-8") as f:
                        return f.read()
                return None
            except Exception as e:
                print(f"Error during merged pipeline processing: {e}")
                return None
        
        return None

    def process_file_content(self, file_content: str, file_id: str,
                             chunk_size: int = 100, overlap_size: int = 20):
        if not file_content:
            return []

        documents = [
            {
                "page_content": file_content,
                "source": file_id
            }
        ]

        # Run semantic chunking (which is heading-based and cleans slides artifacts)
        chunks = chunker_module.chunk_documents(documents)

        # Wrap in CustomDocument objects to conform to the route expectations
        doc_chunks = []
        for i, chunk in enumerate(chunks):
            doc_chunks.append(
                CustomDocument(
                    page_content=chunk["chunk_content"],
                    metadata={
                        "section_heading": chunk.get("section_heading", ""),
                        "chunk_index": chunk.get("chunk_index", i),
                        "token_count": chunk.get("token_count", 0),
                        "source": chunk.get("source", file_id),
                        "source_path": chunk.get("source_path", file_id)
                    }
                )
            )

        return doc_chunks
