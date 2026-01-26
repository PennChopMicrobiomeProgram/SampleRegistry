from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


class Base(DeclarativeBase):
    pass


lane_sample_association = Table(
    "lane_sample_association",
    Base.metadata,
    Column("lane_accession", ForeignKey("lanes.lane_accession"), primary_key=True),
    Column(
        "sample_accession", ForeignKey("samples.sample_accession"), primary_key=True
    ),
)


class Run(Base):
    __tablename__ = "runs"
    run_accession: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_date: Mapped[str]
    machine_type: Mapped[str]
    machine_kit: Mapped[str]
    comment: Mapped[str]
    admin_comment: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"Run(run_accession={self.run_accession}, run_date={self.run_date}, machine_type={self.machine_type}, machine_kit={self.machine_kit}, comment={self.comment}, admin_comment={self.admin_comment})"


class Lane(Base):
    __tablename__ = "lanes"
    lane_accession: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    lane_number: Mapped[int]
    run_accession: Mapped[int] = mapped_column(ForeignKey("runs.run_accession"))
    data_uri: Mapped[str] = mapped_column(nullable=True)
    samples: Mapped[Optional[list["Sample"]]] = relationship(
        secondary=lane_sample_association, backref="lanes", back_populates="samples"
    )

    def __repr__(self):
        return f"Lane(lane_accession={self.lane_accession}, lane_number={self.lane_number}, run_accession={self.run_accession}, data_uri={self.data_uri})"


class Sample(Base):
    __tablename__ = "samples"
    sample_accession: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sample_name: Mapped[str]
    lanes: Mapped[Optional[list["Lane"]]] = relationship(
        secondary=lane_sample_association, backref="samples", back_populates="lanes"
    )
    barcode_sequence: Mapped[str]
    primer_sequence: Mapped[Optional[str]] = mapped_column(nullable=True)
    sample_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    host_species: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"Sample(sample_accession={self.sample_accession}, sample_name={self.sample_name}, barcode_sequence={self.barcode_sequence}, primer_sequence={self.primer_sequence}, sample_type={self.sample_type}, subject_id={self.subject_id}, host_species={self.host_species})"


class Annotation(Base):
    __tablename__ = "annotations"
    sample_accession: Mapped[int] = mapped_column(
        ForeignKey("samples.sample_accession"), primary_key=True
    )
    key: Mapped[str] = mapped_column(primary_key=True)
    val: Mapped[str]

    def __repr__(self):
        return f"Annotation(sample_accession={self.sample_accession}, key={self.key}, val={self.val})"


class StandardSampleType(Base):
    __tablename__ = "standard_sample_types"
    sample_type: Mapped[str] = mapped_column(primary_key=True)
    rarity: Mapped[str]
    host_associated: Mapped[bool]
    comment: Mapped[Optional[str]] = mapped_column(nullable=True)

    def __repr__(self):
        return f"StandardSampleType(sample_type={self.sample_type}, rarity={self.rarity}, host_associated={self.host_associated}, comment={self.comment})"


class StandardHostSpecies(Base):
    __tablename__ = "standard_host_species"
    host_species: Mapped[str] = mapped_column(primary_key=True)
    scientific_name: Mapped[str]
    ncbi_taxon_id: Mapped[int]

    def __repr__(self):
        return f"StandardHostSpecies(host_species={self.host_species}, scientific_name={self.scientific_name}, ncbi_taxon_id={self.ncbi_taxon_id})"
