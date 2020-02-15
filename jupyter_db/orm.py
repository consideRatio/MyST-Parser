import datetime

from sqlalchemy import CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlalchemy import DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.declarative import declared_attr, declarative_base


class DeclarativeBase:
    @staticmethod
    def get_current_time():
        return datetime.datetime.utcnow()


OrmBase = declarative_base(cls=DeclarativeBase)


class OrmDocument(OrmBase):
    __tablename__ = "documents"

    pk = Column(Integer(), primary_key=True)
    uri = Column(String(255), nullable=False, unique=True)
    meta_data = Column(JSON())

    kernels = relationship(
        "OrmKernel",
        back_populates="document",
        order_by="OrmKernel.doc_order",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )
    codecells = relationship(
        "OrmCodeCell",
        back_populates="document",
        order_by="OrmCodeCell.doc_order",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(pk={self.pk}, status={self.status})"


class OrmKernel(OrmBase):
    __tablename__ = "kernels"
    __table_args__ = (
        CheckConstraint(
            "(doc_pk is not null AND doc_order is not null) or "
            "(doc_pk is null AND doc_order is null)",
            name="doc_order_check",
        ),
        UniqueConstraint("doc_pk", "doc_order", name="doc_order"),
    )

    pk = Column(Integer(), primary_key=True)
    name = Column(String(36), nullable=True, unique=True)
    # The type name of the kernel,
    # as reported by executing 'jupyter kernelspec list' on the command line.
    kernel_type = Column(String(36), nullable=False)
    meta_data = Column(JSON())

    # The kernel can be referenced by multiple OrmCodeCell,
    # and the kernel should not be allowed to be deleted,
    # whilst referencing OrmCodeCells exist.
    codecells = relationship(
        "OrmCodeCell",
        back_populates="kernel",
        order_by="OrmCodeCell.exec_order",
        passive_deletes="all",
    )
    # The kernel can be referenced by a single OrmKernelInfo,
    # which should be deleted if the kernel is deleted.
    info = relationship(
        "OrmKernelInfo",
        back_populates="kernel",
        uselist=False,
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    doc_pk = Column(Integer(), ForeignKey("documents.pk", ondelete="CASCADE"))
    document = relationship("OrmDocument", back_populates="kernels")
    doc_order = Column(Integer())

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pk={self.pk}, name={self.name}, "
            f"doc_pk={self.doc_pk}, status={self.status})"
        )


class OrmKernelInfo(OrmBase):
    __tablename__ = "kernelinfo"

    # The kernel info references a single OrmKernel
    pk = Column(
        Integer(), ForeignKey("kernels.pk", ondelete="CASCADE"), primary_key=True
    )
    kernel = relationship("OrmKernel", back_populates="info")
    data = Column(JSON(), nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(pk={self.pk})"


class OrmCodeCell(OrmBase):
    __tablename__ = "codecells"
    __table_args__ = (
        CheckConstraint(
            "(doc_pk is not null AND doc_order is not null) or "
            "(doc_pk is null AND doc_order is null)",
            name="doc_order_check",
        ),
        UniqueConstraint("doc_pk", "doc_order", name="doc_order"),
        UniqueConstraint("kernel_pk", "exec_order", name="exec_order"),
    )

    pk = Column(Integer(), primary_key=True)
    name = Column(String(36), nullable=True, unique=True)
    source = Column(Text(), nullable=False)
    meta_data = Column(JSON())

    # The cell should be related to a kernel, with an order of execution
    kernel_pk = Column(
        Integer(), ForeignKey("kernels.pk", ondelete="RESTRICT"), nullable=False
    )
    kernel = relationship("OrmKernel", back_populates="codecells")
    exec_order = Column(Integer(), nullable=False)

    # The cell should be related to a document
    doc_pk = Column(Integer(), ForeignKey("documents.pk", ondelete="CASCADE"))
    document = relationship("OrmDocument", back_populates="codecells")
    doc_order = Column(Integer())

    # The cell may be referenced by a single OrmCellExecution,
    # which should be deleted if the cell is deleted.
    execution = relationship(
        "OrmCellExecution",
        back_populates="codecell",
        uselist=False,
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pk={self.pk}, doc_pk={self.doc_pk}, "
            f"doc_order={self.doc_order_code}, "
            f"follows={self.follows_pk}, kernel={self.kernel_pk}, status={self.status})"
        )


class OrmCellExecution(OrmBase):
    __tablename__ = "cellexecute"

    pk = Column(
        Integer(), ForeignKey("codecells.pk", ondelete="CASCADE"), primary_key=True
    )
    codecell = relationship("OrmCodeCell", back_populates="execution")

    execution_count = Column(Integer())
    outputs = relationship(
        "OrmOutput",
        order_by="OrmOutput.order",
        back_populates="execute",
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )

    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(pk={self.pk}, count={self.execution_count})"


class OrmOutput(OrmBase):
    __tablename__ = "outputs"
    __table_args__ = (UniqueConstraint("execute_pk", "order", name="execute_order"),)

    pk = Column(Integer(), primary_key=True)
    execute_pk = Column(
        Integer(), ForeignKey("cellexecute.pk", ondelete="CASCADE"), nullable=False
    )
    order = Column(Integer(), nullable=False)
    execute = relationship("OrmCellExecution", back_populates="outputs")
    output_type = Column(Enum("stream", "display_data", "execute_result", "error"))

    __mapper_args__ = {"polymorphic_identity": "outputs", "polymorphic_on": output_type}

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pk={self.pk}, execute_pk={self.execute_pk}, "
            f"order={self.order})"
        )


class OrmOutputStream(OrmOutput):
    __mapper_args__ = {"polymorphic_identity": "stream"}
    name = Column(Enum("stdout", "stderr"))
    text = Column(Text())


class OrmOutputDisplay(OrmOutput):
    __mapper_args__ = {"polymorphic_identity": "display_data"}

    @declared_attr
    def meta_data(cls):
        return OrmOutput.__table__.c.get("meta_data", Column(JSON()))

    data = relationship(
        "OrmMimeBundle",
        collection_class=attribute_mapped_collection("mimetype"),
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )


class OrmOutputExecute(OrmOutput):
    __mapper_args__ = {"polymorphic_identity": "execute_result"}
    execution_count = Column(Integer())

    @declared_attr
    def meta_data(cls):
        return OrmOutput.__table__.c.get("meta_data", Column(JSON()))

    data = relationship(
        "OrmMimeBundle",
        collection_class=attribute_mapped_collection("mimetype"),
        cascade="all, delete, delete-orphan",
        passive_deletes=True,
    )


class OrmOutputError(OrmOutput):
    __mapper_args__ = {"polymorphic_identity": "error"}
    ename = Column(Text())
    evalue = Column(Text())
    # The traceback will contain a list of frames (each as a string)
    traceback = Column(JSON())


class OrmMimeBundle(OrmBase):
    __tablename__ = "mimebundles"
    __table_args__ = (UniqueConstraint("output_pk", "mimetype", name="outputmime"),)

    pk = Column(Integer(), primary_key=True)
    output_pk = Column(Integer(), ForeignKey("outputs.pk", ondelete="CASCADE"))
    mimetype = Column(String(50), nullable=False)
    source = Column(Text(), nullable=False)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(pk={self.pk}, output_pk={self.output_pk}, "
            f"mimetype={self.mimetype})"
        )
