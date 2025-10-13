
import datetime
from typing import Annotated
from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column

intpk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
created_at_col = Annotated[
    datetime.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    ),
]
updated_at_col = Annotated[
    datetime.datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=func.now(),
    ),
]


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )

    repr_cols_num = 3
    repr_cols = ()

    def __repr__(self) -> str:
        """Pretty print the model instance."""
        cols = []
        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f"{col}={getattr(self, col)}")

        return f"<{self.__class__.__name__} {', '.join(cols)}>"