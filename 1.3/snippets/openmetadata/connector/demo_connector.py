"""A custom database connector that reports one database, one schema and one table."""

from typing import Iterable, Optional

from metadata.generated.schema.api.data.createDatabase import CreateDatabaseRequest
from metadata.generated.schema.api.data.createDatabaseSchema import (
    CreateDatabaseSchemaRequest,
)
from metadata.generated.schema.api.data.createTable import CreateTableRequest
from metadata.generated.schema.entity.data.table import Column, DataType
from metadata.generated.schema.metadataIngestion.workflow import (
    Source as WorkflowSource,
)
from metadata.ingestion.api.models import Either
from metadata.ingestion.api.steps import Source
from metadata.ingestion.ometa.ometa_api import OpenMetadata


class DemoSource(Source):
    """Reads no external system: the table it reports is written in the code."""

    def __init__(self, config: WorkflowSource, metadata: OpenMetadata):
        super().__init__()
        self.config = config
        self.metadata = metadata
        self.service = config.serviceName

    @classmethod
    def create(
        cls,
        config_dict: dict,
        metadata: OpenMetadata,
        pipeline_name: Optional[str] = None,
    ) -> "DemoSource":
        return cls(WorkflowSource.model_validate(config_dict), metadata)

    def prepare(self) -> None:
        pass

    def test_connection(self) -> None:
        pass

    def _iter(self, *_, **__) -> Iterable[Either]:
        yield Either(right=CreateDatabaseRequest(name="demo_db", service=self.service))
        yield Either(
            right=CreateDatabaseSchemaRequest(
                name="public", database=f"{self.service}.demo_db"
            )
        )
        yield Either(
            right=CreateTableRequest(
                name="orders",
                databaseSchema=f"{self.service}.demo_db.public",
                columns=[
                    Column(name="id", dataType=DataType.INT),
                    Column(name="amount", dataType=DataType.DOUBLE),
                ],
            )
        )

    def close(self) -> None:
        pass
