import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path


_DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "source_data" / "visa_requirements.json"
)


@dataclass(frozen=True)
class VisaAdvice:
    country_code: str | None
    country_name_vi: str
    country_name_en: str
    status: str
    max_stay_days: int | None
    stay_days: int | None
    entry_date: str | None
    effective_until: str | None
    verified_at: str
    source_url: str
    evisa_url: str
    note_vi: str = ""
    note_en: str = ""

    @property
    def signature(self) -> str:
        return "|".join(
            [
                self.country_code or self.country_name_en,
                self.status,
                str(self.stay_days or ""),
                self.entry_date or "",
                self.verified_at,
            ]
        )

    def render(self, language: str = "vi") -> str:
        return self._render_en() if language == "en" else self._render_vi()

    def _render_vi(self) -> str:
        if self.status == "domestic":
            return ""

        lines = ["### Lưu ý visa và hộ chiếu"]
        if self.status == "visa_exempt":
            lines.append(
                f"Theo dữ liệu được xác minh ngày **{self.verified_at}**, hộ chiếu phổ thông "
                f"do **{self.country_name_vi}** cấp thuộc diện miễn thị thực tối đa "
                f"**{self.max_stay_days} ngày** khi nhập cảnh Việt Nam, nếu đáp ứng các điều kiện nhập cảnh hiện hành."
            )
            if self.stay_days:
                lines.append(
                    f"Thời gian dự kiến **{self.stay_days} ngày** nằm trong giới hạn miễn thị thực nêu trên."
                )
        elif self.status == "exceeds_exemption":
            lines.append(
                f"Hộ chiếu phổ thông do **{self.country_name_vi}** cấp có thời hạn miễn thị thực "
                f"tối đa **{self.max_stay_days} ngày**, trong khi chuyến đi dự kiến là "
                f"**{self.stay_days} ngày**. Hãy kiểm tra loại visa hoặc e-Visa phù hợp trước khi đặt dịch vụ."
            )
        elif self.status == "date_unconfirmed":
            lines.append(
                "Ngày nhập cảnh chưa đủ rõ để đối chiếu thời hạn hiệu lực của chính sách. "
                "Vui lòng cung cấp ngày theo định dạng **YYYY-MM-DD** trước khi sử dụng thông tin miễn thị thực."
            )
        else:
            lines.append(
                f"Dữ liệu cục bộ hiện **chưa xác nhận** chính sách miễn thị thực còn hiệu lực "
                f"cho hộ chiếu phổ thông do **{self.country_name_vi}** cấp. Không nên xem đây là kết luận rằng được miễn hoặc phải xin visa."
            )

        if self.effective_until and self.status in {"visa_exempt", "exceeds_exemption"}:
            lines.append(f"Mốc hiệu lực được ghi nhận đến ngày **{self.effective_until}**.")
        if self.note_vi:
            lines.append(self.note_vi)
        lines.extend(
            [
                "Hãy kiểm tra hộ chiếu còn đủ thời hạn, điều kiện nhập cảnh và chính sách mới nhất trước ngày khởi hành.",
                (
                    f"> **Nguồn:** [Bộ Ngoại giao Việt Nam]({self.source_url}) | "
                    f"[Cổng e-Visa chính thức]({self.evisa_url})\n>\n"
                    "> Thông tin này chỉ mang tính hỗ trợ và không thay thế xác nhận của "
                    "cơ quan xuất nhập cảnh hoặc cơ quan đại diện ngoại giao."
                ),
            ]
        )
        return "\n\n" + "\n\n".join(lines)

    def _render_en(self) -> str:
        if self.status == "domestic":
            return ""

        lines = ["### Visa and passport note"]
        if self.status == "visa_exempt":
            lines.append(
                f"According to data verified on **{self.verified_at}**, ordinary passport holders "
                f"from **{self.country_name_en}** are eligible for visa-free entry for up to "
                f"**{self.max_stay_days} days**, subject to current entry conditions."
            )
            if self.stay_days:
                lines.append(
                    f"The planned stay of **{self.stay_days} days** is within that stated visa-free limit."
                )
        elif self.status == "exceeds_exemption":
            lines.append(
                f"Ordinary passport holders from **{self.country_name_en}** have a stated visa-free "
                f"limit of **{self.max_stay_days} days**, while the planned stay is **{self.stay_days} days**. "
                "Check the appropriate visa or e-Visa before booking travel services."
            )
        elif self.status == "date_unconfirmed":
            lines.append(
                "The entry date is not precise enough to check the policy's effective period. "
                "Provide it as **YYYY-MM-DD** before relying on visa-exemption guidance."
            )
        else:
            lines.append(
                f"The local dataset **does not currently confirm** an active ordinary-passport visa exemption "
                f"for **{self.country_name_en}**. This is not a conclusion that a visa is or is not required."
            )

        if self.effective_until and self.status in {"visa_exempt", "exceeds_exemption"}:
            lines.append(f"The recorded policy is effective through **{self.effective_until}**.")
        if self.note_en:
            lines.append(self.note_en)
        lines.extend(
            [
                "Check passport validity, entry conditions, and the latest policy before departure.",
                (
                    f"> **Sources:** [Vietnam Ministry of Foreign Affairs]({self.source_url}) | "
                    f"[Official e-Visa portal]({self.evisa_url})\n>\n"
                    "> This guidance does not replace confirmation from immigration authorities "
                    "or a Vietnamese diplomatic mission."
                ),
            ]
        )
        return "\n\n" + "\n\n".join(lines)


class VisaAdvisor:
    def __init__(self, data_path: str | Path | None = None):
        path = Path(data_path) if data_path else _DEFAULT_DATA_PATH
        with path.open("r", encoding="utf-8") as file:
            self.data = json.load(file)

        self.verified_at = str(self.data.get("verified_at") or "unknown")
        self.sources = self.data.get("sources") or {}
        self._country_index = {}
        for country in self.data.get("countries", []):
            aliases = {
                str(country.get("code") or ""),
                str(country.get("name_vi") or ""),
                str(country.get("name_en") or ""),
                *country.get("aliases", []),
            }
            for alias in aliases:
                normalized = self._normalize(alias)
                if normalized:
                    self._country_index[normalized] = country

    def is_vietnamese(self, passport_country: str | None) -> bool:
        country = self._find_country(passport_country)
        return bool(country and country.get("code") == "VN")

    def resolve_passport_country(
        self,
        text: str,
        allow_plain: bool = False,
    ) -> str | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        if allow_plain:
            candidates = [normalized]
            origin_match = re.fullmatch(
                r"(?:i(?:\s+am|'m)|im|i\s+come)\s+from\s+(.+)",
                normalized,
            )
            country_match = re.fullmatch(
                r"(?:my\s+country\s+is|toi\s+den\s+tu)\s+(.+)",
                normalized,
            )
            contextual_match = origin_match or country_match
            if contextual_match:
                candidates.insert(0, contextual_match.group(1).strip(" ,.!?"))

            for candidate in candidates:
                exact_country = self._country_index.get(candidate)
                if exact_country:
                    return str(exact_country.get("name_en") or "").strip() or None

        matches = {}
        for alias, country in self._country_index.items():
            if len(alias) < 3:
                continue

            alias_pattern = re.escape(alias)
            before_passport = rf"(?<!\w){alias_pattern}(?!\w)\s+(?:ordinary\s+)?passports?\b"
            after_passport = (
                rf"\bpassports?\s+(?:issued\s+by|from|is)\s+"
                rf"(?<!\w){alias_pattern}(?!\w)"
            )
            if re.search(before_passport, normalized) or re.search(
                after_passport,
                normalized,
            ):
                code = str(country.get("code") or alias)
                matches[code] = country

        if len(matches) != 1:
            return None
        country = next(iter(matches.values()))
        return str(country.get("name_en") or "").strip() or None

    def get_advice(
        self,
        passport_country: str,
        stay_days: int | None = None,
        entry_date: str | None = None,
    ) -> VisaAdvice:
        country = self._find_country(passport_country)
        source_url = str(self.sources.get("mofa") or "")
        evisa_url = str(self.sources.get("evisa") or "")

        if not country:
            display_name = str(passport_country or "Unknown").strip() or "Unknown"
            return VisaAdvice(
                country_code=None,
                country_name_vi=display_name,
                country_name_en=display_name,
                status="unknown",
                max_stay_days=None,
                stay_days=stay_days,
                entry_date=entry_date,
                effective_until=None,
                verified_at=self.verified_at,
                source_url=source_url,
                evisa_url=evisa_url,
            )

        policy = country.get("ordinary_passport") or {}
        status = str(policy.get("status") or "unknown")
        max_stay_days = policy.get("max_stay_days")
        effective_from = self._parse_date(policy.get("effective_from"))
        effective_until = self._parse_date(policy.get("effective_until"))
        parsed_entry_date = self._parse_date(entry_date)
        travel_date = parsed_entry_date or date.today()

        if entry_date and not parsed_entry_date and status == "visa_exempt":
            status = "date_unconfirmed"

        if status == "visa_exempt" and (
            (effective_from and travel_date < effective_from)
            or (effective_until and travel_date > effective_until)
        ):
            status = "unknown"

        if (
            status == "visa_exempt"
            and max_stay_days
            and stay_days
            and stay_days > int(max_stay_days)
        ):
            status = "exceeds_exemption"

        return VisaAdvice(
            country_code=str(country.get("code") or "") or None,
            country_name_vi=str(country.get("name_vi") or passport_country),
            country_name_en=str(country.get("name_en") or passport_country),
            status=status,
            max_stay_days=int(max_stay_days) if max_stay_days else None,
            stay_days=stay_days,
            entry_date=entry_date,
            effective_until=effective_until.isoformat() if effective_until else None,
            verified_at=self.verified_at,
            source_url=source_url,
            evisa_url=evisa_url,
            note_vi=str(policy.get("note_vi") or ""),
            note_en=str(policy.get("note_en") or ""),
        )

    def _find_country(self, passport_country: str | None) -> dict | None:
        normalized = self._normalize(passport_country or "")
        return self._country_index.get(normalized)

    def _normalize(self, value: str) -> str:
        value = unicodedata.normalize("NFD", str(value).lower())
        value = "".join(char for char in value if unicodedata.category(char) != "Mn")
        value = value.replace("đ", "d")
        return " ".join(value.replace(".", " ").split())

    def _parse_date(self, value) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError:
            return None
