from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Time values (lap/sector/pit-stop durations) are stored as fixed-point
# Numeric rather than float, so equality/idempotency checks in the
# repository layer aren't subject to binary floating-point rounding.
_SECONDS = Numeric(7, 3, asdecimal=False)


class RaceSession(Base):
    """A single F1 session (race, qualifying, practice, ...) for one
    year/round, as ingested from FastF1. Named RaceSession (not Session) to
    avoid clashing with SQLAlchemy's own Session/AsyncSession classes."""

    __tablename__ = "race_sessions"
    __table_args__ = (
        UniqueConstraint("year", "round", "session_type", name="uq_session_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    session_type: Mapped[str] = mapped_column(String(16), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_laps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    laps: Mapped[list["Lap"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Lap.lap_number"
    )
    pit_stops: Mapped[list["PitStop"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="PitStop.lap_number"
    )
    stints: Mapped[list["Stint"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Stint.stint_number"
    )
    drivers: Mapped[list["Driver"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Driver.id"
    )
    results: Mapped[list["DriverResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="DriverResult.id"
    )


class Lap(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("race_sessions.id", ondelete="CASCADE"))

    driver: Mapped[str] = mapped_column(String(8), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    sector_1_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    sector_2_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    sector_3_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    compound: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tyre_life: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    session: Mapped[RaceSession] = relationship(back_populates="laps")


class PitStop(Base):
    __tablename__ = "pit_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("race_sessions.id", ondelete="CASCADE"))

    driver: Mapped[str] = mapped_column(String(8), nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)

    session: Mapped[RaceSession] = relationship(back_populates="pit_stops")


class Stint(Base):
    __tablename__ = "stints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("race_sessions.id", ondelete="CASCADE"))

    driver: Mapped[str] = mapped_column(String(8), nullable=False)
    stint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    compound: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_lap: Mapped[int] = mapped_column(Integer, nullable=False)
    end_lap: Mapped[int] = mapped_column(Integer, nullable=False)

    session: Mapped[RaceSession] = relationship(back_populates="stints")


class Driver(Base):
    """Static per-driver info for a session (name/number/team), separate
    from Lap since it doesn't vary lap to lap — see
    fastf1_client._build_drivers."""

    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("race_sessions.id", ondelete="CASCADE"))

    code: Mapped[str] = mapped_column(String(8), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    session: Mapped[RaceSession] = relationship(back_populates="drivers")


class DriverResult(Base):
    """Final classification for one driver in a session — see
    fastf1_client._build_results. Separate from Driver (static
    name/number/team info) since this is outcome data, not identity."""

    __tablename__ = "driver_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("race_sessions.id", ondelete="CASCADE"))

    code: Mapped[str] = mapped_column(String(8), nullable=False)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classified_position: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    total_time_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    gap_to_leader_seconds: Mapped[float | None] = mapped_column(_SECONDS, nullable=True)
    points: Mapped[float | None] = mapped_column(Numeric(6, 2, asdecimal=False), nullable=True)

    session: Mapped[RaceSession] = relationship(back_populates="results")
