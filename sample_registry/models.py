from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"
    run_accession: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[str]
    machine_type: Mapped[str]
    machine_kit: Mapped[str]
    lane: Mapped[int]
    data_uri: Mapped[str]
    comment: Mapped[str]
    admin_comment: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"Run(run_accession={self.run_accession}, run_date={self.run_date}, machine_type={self.machine_type}, machine_kit={self.machine_kit}, lane={self.lane}, data_uri={self.data_uri}, comment={self.comment}, admin_comment={self.admin_comment})"


class Sample(Base):
    __tablename__ = "samples"
    sample_accession: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sample_name: Mapped[str]
    run_accession: Mapped[int] = mapped_column(ForeignKey("runs.run_accession"))
    barcode_sequence: Mapped[str]
    primer_sequence: Mapped[Optional[str]] = mapped_column(nullable=True)
    sample_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    host_species: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"Sample(sample_accession={self.sample_accession}, sample_name={self.sample_name}, run_accession={self.run_accession}, barcode_sequence={self.barcode_sequence}, primer_sequence={self.primer_sequence}, sample_type={self.sample_type}, subject_id={self.subject_id}, host_species={self.host_species})"


class Annotation(Base):
    __tablename__ = "annotations"
    sample_accession: Mapped[int] = mapped_column(
        ForeignKey("samples.sample_accession"), primary_key=True
    )
    key: Mapped[str] = mapped_column(primary_key=True)
    val: Mapped[str]

    def __repr__(self):
        return f"Annotation(sample_accession={self.sample_accession}, key={self.key}, val={self.val})"


