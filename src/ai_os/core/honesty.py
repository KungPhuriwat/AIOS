from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import TaskResult


@dataclass
class HonestyReport:
    knows: bool
    inferred: bool
    confidence: float
    statement: str


class HonestyLayer:
    def build_report(self, result: TaskResult) -> HonestyReport:
        knows = result.confidence >= 0.75 and not result.inferred
        if knows:
            statement = "ข้อมูลนี้อยู่ในขอบเขตที่ AI มั่นใจสูงและมีหลักฐานรองรับ"
        elif result.inferred:
            statement = "คำตอบนี้มีส่วนที่เป็นการอนุมาน ควรตรวจสอบเพิ่มเติม"
        else:
            statement = "ความมั่นใจระดับกลาง ควรยืนยันด้วยการทดสอบจริง"

        return HonestyReport(
            knows=knows,
            inferred=result.inferred,
            confidence=result.confidence,
            statement=statement,
        )

    def as_dict(self, result: TaskResult) -> dict:
        return asdict(self.build_report(result))
