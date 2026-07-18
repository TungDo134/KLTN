import asyncio
import json
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class RoutingContext:
    response_language: str = "vi"
    passport_country: str | None = None
    pending_question: str | None = None
    pending_intent: str | None = None
    pending_stay_days: int | None = None
    pending_entry_date: str | None = None
    visa_note_signature: str | None = None


@dataclass
class RouteDecision:
    intent: str
    action: str
    confidence: float
    reply: str | None = None
    reason: str = ""
    language: str = "unknown"
    response_language: str = "vi"
    passport_country: str | None = None
    resolved_question: str | None = None
    stay_days: int | None = None
    entry_date: str | None = None


_SMALL_TALK_PHRASES = {
    "hi",
    "hello",
    "xin chao",
    "chao",
    "chao ban",
    "cam on",
    "thanks",
    "thank you",
    "tam biet",
    "bye",
}

_VI_SMALL_TALK = {"xin chao", "chao", "chao ban", "cam on", "tam biet"}

_DETAIL_HELP_PHRASES = {
    "what do you need",
    "specifically what do you need",
    "what information do you need",
    "what should i provide",
    "can thong tin gi",
    "toi can cung cap gi",
    "can cu the thong tin gi",
}

_DESTINATION_PHRASES = {
    "viet nam",
    "da lat",
    "dalat",
    "da nang",
    "ha noi",
    "hanoi",
    "sai gon",
    "ho chi minh",
    "nha trang",
    "vung tau",
    "hue",
    "hoi an",
    "sapa",
    "sa pa",
    "phu quoc",
    "moc chau",
    "ha giang",
}

_TRAVEL_GENERAL_PHRASES = {
    "du lich",
    "travel",
    "tham quan",
    "tourism",
    "packing",
    "di bien",
    "mang theo",
    "nen mang",
    "mang gi khi di",
    "travel advice",
    "travel tips",
}

_RECOMMENDATION_PHRASES = {
    "dia diem tham quan",
    "goi y dia diem",
    "diem den",
    "nen di dau",
    "quan an",
    "khach san",
    "homestay",
    "thoi tiet",
    "where should i go",
    "places to visit",
    "recommend a place",
    "hotel",
    "weather",
}

_PLANNING_PHRASES = {
    "lich trinh",
    "hanh trinh",
    "trip plan",
    "travel plan",
    "plan a trip",
    "itinerary",
}

_VIETNAMESE_LANGUAGE_PHRASES = {
    "toi",
    "muon",
    "du lich",
    "lich trinh",
    "o dau",
    "nen",
    "goi y",
    "dia diem",
    "tham quan",
    "di bien",
    "mang theo",
    "nhung gi",
    "viet cho",
    "doc file",
    "ho chieu",
    "mien thi thuc",
}

_ENGLISH_LANGUAGE_MARKERS = {
    "i",
    "you",
    "we",
    "my",
    "our",
    "the",
    "to",
    "in",
    "for",
    "from",
    "with",
    "and",
    "is",
    "are",
    "do",
    "does",
    "can",
    "could",
    "would",
    "should",
    "please",
    "want",
    "need",
    "have",
    "use",
    "tell",
    "write",
    "read",
    "create",
    "explain",
    "show",
    "code",
    "python",
    "file",
    "csv",
    "cost",
    "price",
    "pricing",
    "calculate",
    "estimate",
    "email",
    "joke",
    "story",
    "travel",
    "trip",
    "plan",
    "itinerary",
    "visit",
    "visiting",
    "explore",
    "recommend",
    "suggest",
    "place",
    "places",
    "destination",
    "hotel",
    "hotels",
    "weather",
    "passport",
    "passports",
    "visa",
    "day",
    "days",
    "food",
    "restaurant",
    "restaurants",
    "museum",
    "museums",
    "beach",
    "beaches",
    "cafe",
    "cafes",
    "best",
    "around",
    "where",
    "what",
    "how",
}

_ENGLISH_STRUCTURE_MARKERS = {
    "i",
    "you",
    "we",
    "my",
    "our",
    "the",
    "to",
    "in",
    "for",
    "from",
    "with",
    "and",
    "do",
    "does",
    "could",
    "would",
    "should",
    "please",
    "want",
    "need",
    "have",
    "use",
    "where",
    "what",
    "how",
}

_INVALID_PASSPORT_COUNTRIES = {
    "unknown",
    "uncertain",
    "multiple",
    "multiple countries",
    "not specified",
    "n a",
    "none",
    "null",
    "i dont know",
    "i do not know",
    "not sure",
    "khong biet",
    "chua ro",
}

_VISA_PHRASES = {
    "visa",
    "evisa",
    "e visa",
    "passport",
    "passports",
    "ho chieu",
    "mien thi thuc",
    "thi thuc",
}

_VALID_INTENTS = {
    "small_talk",
    "not_travel",
    "uncertain",
    "visa_advice",
    "travel_general",
    "travel_recommendation",
    "trip_planning",
}

_TRAVEL_INTENTS = {
    "travel_general",
    "travel_recommendation",
    "trip_planning",
}

_ACTION_BY_INTENT = {
    "travel_general": "direct_answer",
    "travel_recommendation": "run_recommendation",
    "trip_planning": "run_planning",
}


class QueryRouter:
    def __init__(
        self,
        llm=None,
        timeout_seconds: float = 8.0,
        passport_country_resolver=None,
    ):
        self.llm = llm
        self.timeout_seconds = timeout_seconds
        self.passport_country_resolver = passport_country_resolver

    async def route(
        self,
        question: str,
        history: list | None = None,
        context: RoutingContext | None = None,
    ) -> RouteDecision:
        history = history or []
        context = context or RoutingContext()
        normalized = self._normalize(question)

        if not normalized or normalized in {"?", ".", "...", "!"}:
            return self._fast_reply(
                intent="small_talk",
                reply=self._reply("empty", context.response_language),
                confidence=1.0,
                reason="Empty or too short query.",
                language="unknown",
                response_language=context.response_language,
            )

        if (
            not history
            and not context.pending_question
            and self._is_small_talk_only(normalized)
        ):
            response_language = (
                "vi" if normalized in _VI_SMALL_TALK else "en"
            )
            context.response_language = response_language
            return self._fast_reply(
                intent="small_talk",
                reply=self._reply("small_talk", response_language),
                confidence=1.0,
                reason="Exact small-talk phrase.",
                language=response_language,
                response_language=response_language,
            )

        if self._contains_phrase(normalized, _DETAIL_HELP_PHRASES):
            detected_language = self._detect_supported_language(
                question,
                normalized,
            )
            response_language = (
                detected_language
                if detected_language in {"vi", "en"}
                else context.response_language
            )
            context.response_language = response_language
            return self._fast_reply(
                intent="uncertain",
                reply=self._reply("uncertain", response_language),
                confidence=1.0,
                reason="User asked which trip details should be provided.",
                language=detected_language,
                response_language=response_language,
                resolved_question=context.pending_question,
            )

        data = await self._classify(question, history, context)
        rule_data = self._classify_by_rules(question, context)
        is_pending_country_answer = bool(
            context.pending_question
            and (
                len(re.findall(r"\b\w+\b", normalized)) <= 3
                or self._looks_like_origin_answer(normalized)
            )
        )
        data = self._merge_classification(
            data,
            rule_data,
            preserve_language=is_pending_country_answer,
        )
        if is_pending_country_answer:
            data["language"] = "unknown"
            data["response_language"] = context.response_language

        language = str(data.get("language") or "unknown").strip().lower()
        if language not in {"vi", "en", "mixed", "unsupported", "unknown"}:
            language = "unknown"

        response_language = str(
            data.get("response_language") or context.response_language or "vi"
        ).strip().lower()
        if response_language not in {"vi", "en"}:
            response_language = context.response_language or "vi"
        context.response_language = response_language

        if language == "unsupported":
            return self._fast_reply(
                intent="unsupported_language",
                reply=self._reply("unsupported", response_language),
                confidence=self._confidence(data),
                reason=str(data.get("_reason") or "Unsupported input language."),
                language=language,
                response_language=response_language,
            )

        intent = str(data.get("intent") or "uncertain").strip().lower()
        if intent not in _VALID_INTENTS:
            intent = "uncertain"

        confidence = self._confidence(data)
        raw_passport_country = self._optional_text(data.get("passport_country"))
        ambiguous_passport_country = self._is_ambiguous_korea(normalized)
        multiple_passports = self._as_bool(data.get("multiple_passports")) or (
            self._mentions_multiple_passports(normalized)
        )
        can_accept_passport_country = bool(
            context.pending_question
            or self._contains_phrase(
                normalized,
                {"passport", "passports", "ho chieu"},
            )
        )
        resolved_passport_country = self._resolve_passport_country(
            question,
            allow_plain=is_pending_country_answer,
        )
        short_country_fallback = (
            question.strip()
            if (
                is_pending_country_answer
                and self._looks_like_country_answer(normalized)
            )
            else None
        )
        passport_candidate = (
            resolved_passport_country
            or self._valid_passport_country(raw_passport_country)
            or short_country_fallback
        )
        passport_country = (
            None
            if (
                ambiguous_passport_country
                or multiple_passports
                or not can_accept_passport_country
            )
            else passport_candidate
        )
        invalid_passport_value = bool(
            can_accept_passport_country
            and raw_passport_country
            and not passport_country
        )

        if ambiguous_passport_country or multiple_passports:
            context.passport_country = None
        elif passport_country:
            context.passport_country = passport_country
        else:
            passport_country = context.passport_country

        pending_question = context.pending_question
        pending_intent = context.pending_intent
        resolved_question = (
            self._optional_text(data.get("resolved_question"))
            if pending_question
            else None
        )
        if pending_question:
            resolved_question = self._merge_pending_trip_details(
                pending_question,
                question,
                pending_intent,
            )

        if pending_question and passport_country:
            if pending_intent in _VALID_INTENTS:
                intent = pending_intent
            elif intent not in _TRAVEL_INTENTS | {"visa_advice"}:
                restored = self._classify_by_rules(pending_question, context)
                restored_intent = str(restored.get("intent") or "uncertain")
                if restored_intent in _TRAVEL_INTENTS | {"visa_advice"}:
                    intent = restored_intent
        elif (
            pending_question
            and invalid_passport_value
            and pending_intent in _TRAVEL_INTENTS | {"visa_advice"}
        ):
            intent = pending_intent

        if confidence < 0.55 and not (
            pending_question
            and (passport_country or invalid_passport_value or multiple_passports)
        ):
            intent = "uncertain"

        stay_days = self._optional_positive_int(data.get("stay_days"))
        entry_date = self._optional_text(data.get("entry_date"))
        if pending_question:
            stay_days = stay_days or context.pending_stay_days
            entry_date = entry_date or context.pending_entry_date

        common = {
            "confidence": confidence,
            "language": language,
            "response_language": response_language,
            "passport_country": passport_country,
            "resolved_question": resolved_question,
            "stay_days": stay_days,
            "entry_date": entry_date,
        }

        if ambiguous_passport_country:
            route_intent = (
                pending_intent
                if pending_intent in _TRAVEL_INTENTS | {"visa_advice"}
                else intent
            )
            if route_intent not in _TRAVEL_INTENTS | {"visa_advice"}:
                route_intent = "visa_advice"

            context.pending_question = pending_question or question
            context.pending_intent = route_intent
            context.pending_stay_days = stay_days
            context.pending_entry_date = entry_date
            return RouteDecision(
                intent=route_intent,
                action="ask_country",
                reply=self._reply("clarify_korea", response_language),
                reason="Korea must be clarified as South Korea or North Korea.",
                **common,
            )

        if multiple_passports:
            route_intent = (
                pending_intent
                if pending_intent in _TRAVEL_INTENTS | {"visa_advice"}
                else intent
            )
            if route_intent not in _TRAVEL_INTENTS | {"visa_advice"}:
                route_intent = "visa_advice"

            context.pending_question = pending_question or question
            context.pending_intent = route_intent
            context.pending_stay_days = stay_days
            context.pending_entry_date = entry_date
            return RouteDecision(
                intent=route_intent,
                action="ask_country",
                reply=self._reply("ask_country", response_language),
                reason="Multiple passports require an explicit passport choice.",
                **common,
            )

        if intent == "small_talk":
            return self._fast_reply(
                intent=intent,
                reply=self._reply("small_talk", response_language),
                reason="Classifier detected small talk.",
                **common,
            )

        if intent == "not_travel":
            return self._fast_reply(
                intent=intent,
                reply=self._reply("not_travel", response_language),
                reason="Classifier rejected the travel domain.",
                **common,
            )

        if intent == "uncertain":
            return self._fast_reply(
                intent=intent,
                reply=self._reply("uncertain", response_language),
                reason=str(data.get("_reason") or "Classifier result is uncertain."),
                **common,
            )

        needs_country = not passport_country and (
            intent == "visa_advice"
            or (intent in _TRAVEL_INTENTS and language == "en")
        )
        if needs_country:
            context.pending_question = resolved_question or question
            context.pending_intent = intent
            context.pending_stay_days = stay_days
            context.pending_entry_date = entry_date
            return RouteDecision(
                intent=intent,
                action="ask_country",
                reply=self._reply(
                    "ask_country_plan"
                    if intent == "trip_planning" and not pending_question
                    else "ask_country",
                    response_language,
                ),
                reason="Passport country is required before continuing.",
                **common,
            )

        context.pending_question = None
        context.pending_intent = None
        context.pending_stay_days = None
        context.pending_entry_date = None

        if intent == "visa_advice":
            return RouteDecision(
                intent=intent,
                action="visa_reply",
                reason="Visa advice can be answered without the travel pipeline.",
                **common,
            )

        return RouteDecision(
            intent=intent,
            action=_ACTION_BY_INTENT[intent],
            reason="Travel task confirmed by the classifier.",
            **common,
        )

    async def _classify(
        self,
        question: str,
        history: list,
        context: RoutingContext,
    ) -> dict:
        if not self.llm:
            return self._classify_by_rules(question, context)

        prompt = self._build_classifier_prompt(question, history, context)
        try:
            response = await asyncio.wait_for(
                self.llm.ainvoke(prompt),
                timeout=self.timeout_seconds,
            )
            text = getattr(response, "content", str(response))
            return self._parse_json(text)
        except Exception as exc:
            fallback = self._classify_by_rules(question, context)
            fallback["_reason"] = f"LLM classifier failed: {type(exc).__name__}"
            return fallback

    def _build_classifier_prompt(
        self,
        question: str,
        history: list,
        context: RoutingContext,
    ) -> str:
        history_text = self._history_to_text(history[-8:]) or "(none)"
        pending_question = context.pending_question or "(none)"
        pending_intent = context.pending_intent or "(none)"
        known_country = context.passport_country or "(unknown)"

        return f"""
You are a strict routing classifier for a chatbot that only supports travel in Vietnam.
Do not answer the user. Return one JSON object only.

Language policy:
- Accept Vietnamese, English, or a Vietnamese-English mix.
- Use "unsupported" for any other language.
- Classify the CURRENT message language before considering history.
- Technical words such as Python, CSV, API, hotel, or visa do not change the surrounding language.
- "response_language" must match a clearly Vietnamese or English current message.
- For mixed text, choose the dominant language.
- A place name or country name alone can be "unknown" and should inherit the conversation language.

Intent policy:
- "small_talk": greeting, thanks, goodbye only.
- "not_travel": unrelated to travel in Vietnam.
- "uncertain": insufficient evidence.
- "visa_advice": visa, entry, or passport requirements for travel to Vietnam.
- "travel_general": general Vietnam travel guidance that does not need place retrieval or an itinerary.
- "travel_recommendation": asks for places, food, hotels, destination suggestions, or weather, but not a day-by-day plan.
- "trip_planning": asks for an itinerary, schedule, route, or a trip lasting a stated number of days.
- A visa question that only mentions stay duration remains "visa_advice" unless it explicitly asks for a plan or itinerary.

Passport policy:
- Never infer nationality from language, name, email, or writing style.
- Extract passport_country only when the user explicitly states the passport they will use.
- When a passport-country question is pending, treat "I'm from X" as the user's contextual answer for the passport country.
- If multiple passports are mentioned without choosing one, leave passport_country null and set multiple_passports to true.
- Preserve the primary travel intent when multiple passports are mentioned.
- If the current message answers a previous passport-country question, keep the pending travel intent and return the original travel request in resolved_question.

Examples:
- "Viết cho tôi code Python" -> language vi, response_language vi, intent not_travel.
- "Bonjour, je veux visiter le Vietnam" -> language unsupported.
- "Đi biển ở Việt Nam nên mang theo gì?" -> language vi, intent travel_general.
- "Gợi ý địa điểm tham quan ở Đà Nẵng" -> language vi, intent travel_recommendation.
- "Plan a 3-day trip to Da Nang" -> language en, response_language en, intent trip_planning.
- Pending passport question + "I'm from China" -> passport_country China and preserve the pending travel intent.
- "I have German and US passports" -> language en, passport_country null, multiple_passports true.

Known routing context:
- response_language: {context.response_language}
- passport_country: {known_country}
- pending_intent: {pending_intent}
- pending_question: {pending_question}

Recent role-labelled history:
{history_text}

Current message:
{question}

Return exactly this shape:
{{
  "language": "vi | en | mixed | unsupported | unknown",
  "response_language": "vi | en",
  "intent": "small_talk | not_travel | uncertain | visa_advice | travel_general | travel_recommendation | trip_planning",
  "confidence": 0.0,
  "passport_country": null,
  "multiple_passports": false,
  "resolved_question": null,
  "stay_days": null,
  "entry_date": null
}}

Use YYYY-MM-DD for entry_date only when the exact date is explicit and valid;
otherwise return null.
""".strip()

    def _classify_by_rules(self, question: str, context: RoutingContext) -> dict:
        normalized = self._normalize(question)
        language = self._detect_supported_language(question, normalized)
        response_language = (
            language if language in {"vi", "en"} else context.response_language
        )

        intent = "uncertain"
        confidence = 0.45
        has_explicit_planning_signal = self._has_explicit_planning_signal(
            normalized
        )
        has_duration_signal = bool(
            re.search(r"\b\d+\s*-?\s*(ngay|day|days)\b", normalized)
        )
        has_recommendation_signal = self._contains_phrase(
            normalized,
            _RECOMMENDATION_PHRASES,
        )
        has_visa_signal = self._contains_phrase(normalized, _VISA_PHRASES)

        if self._is_small_talk_only(normalized):
            intent = "small_talk"
            confidence = 0.95
        elif has_explicit_planning_signal:
            intent = "trip_planning"
            confidence = 0.75
        elif has_recommendation_signal:
            intent = "travel_recommendation"
            confidence = 0.7
        elif has_visa_signal:
            intent = "visa_advice"
            confidence = 0.8
        elif has_duration_signal:
            intent = "trip_planning"
            confidence = 0.75
        elif self._contains_phrase(normalized, _TRAVEL_GENERAL_PHRASES):
            intent = "travel_general"
            confidence = 0.7
        elif self._contains_phrase(normalized, _DESTINATION_PHRASES):
            intent = "uncertain"
            confidence = 0.5
        else:
            intent = "not_travel"
            confidence = 0.65

        return {
            "language": language,
            "response_language": response_language,
            "intent": intent,
            "confidence": confidence,
            "passport_country": context.passport_country,
            "multiple_passports": self._mentions_multiple_passports(normalized),
            "resolved_question": context.pending_question,
            "stay_days": None,
            "entry_date": None,
            "_reason": "Rule-based fallback classification.",
        }

    def _merge_classification(
        self,
        data: dict,
        rule_data: dict,
        preserve_language: bool = False,
    ) -> dict:
        merged = dict(data)
        overrides = []

        classifier_language = str(
            data.get("language") or "unknown"
        ).strip().lower()
        rule_language = str(
            rule_data.get("language") or "unknown"
        ).strip().lower()
        if (
            not preserve_language
            and rule_language in {"vi", "en", "unsupported"}
        ):
            merged["language"] = rule_language
            if rule_language in {"vi", "en"}:
                merged["response_language"] = rule_language
            overrides.append(f"language={rule_language}")

        classifier_intent = str(
            data.get("intent") or "uncertain"
        ).strip().lower()
        rule_intent = str(
            rule_data.get("intent") or "uncertain"
        ).strip().lower()
        classifier_confidence = self._confidence(data)
        strong_rule_intents = _TRAVEL_INTENTS | {"small_talk", "visa_advice"}

        should_use_rule_intent = (
            rule_intent in strong_rule_intents
            and (
                classifier_intent not in _VALID_INTENTS
                or classifier_intent in {"uncertain", "not_travel"}
                or classifier_confidence < 0.55
                or (
                    classifier_language == "unsupported"
                    and rule_language in {"vi", "en"}
                )
                or (
                    rule_intent == "visa_advice"
                    and classifier_intent in _TRAVEL_INTENTS
                )
                or (
                    rule_intent == "trip_planning"
                    and classifier_intent == "visa_advice"
                )
            )
        )
        should_use_rule_not_travel = (
            rule_intent == "not_travel"
            and (
                classifier_intent in {"uncertain", "not_travel"}
                or (
                    classifier_language == "unsupported"
                    and rule_language in {"vi", "en"}
                )
            )
        )
        if should_use_rule_intent or should_use_rule_not_travel:
            merged["intent"] = rule_intent
            merged["confidence"] = max(
                classifier_confidence,
                self._confidence(rule_data),
            )
            overrides.append(f"intent={rule_intent}")

        if overrides:
            existing_reason = str(data.get("_reason") or "").strip()
            validation_reason = "Rule post-validation: " + ", ".join(overrides)
            merged["_reason"] = "; ".join(
                reason for reason in [existing_reason, validation_reason] if reason
            )
        return merged

    def _has_explicit_planning_signal(self, normalized: str) -> bool:
        return bool(
            self._contains_phrase(normalized, _PLANNING_PHRASES)
            or re.search(r"\bplan\b.*\btrip\b", normalized)
        )

    def _mentions_multiple_passports(self, normalized: str) -> bool:
        english_multiple = (
            "passports" in normalized
            and bool(re.search(r"\b(and|or)\b", normalized))
        )
        vietnamese_multiple = (
            self._contains_phrase(normalized, {"hai ho chieu", "nhieu ho chieu"})
            and bool(re.search(r"\b(va|hoac)\b", normalized))
        )
        return english_multiple or vietnamese_multiple

    def _valid_passport_country(self, value) -> str | None:
        text = self._optional_text(value)
        if not text:
            return None
        if self._normalize(text) in _INVALID_PASSPORT_COUNTRIES:
            return None
        return text

    def _resolve_passport_country(
        self,
        text: str,
        allow_plain: bool,
    ) -> str | None:
        if not self.passport_country_resolver:
            return None
        try:
            return self.passport_country_resolver(
                text,
                allow_plain=allow_plain,
            )
        except Exception:
            return None

    def _looks_like_country_answer(self, normalized: str) -> bool:
        if not normalized or normalized in _INVALID_PASSPORT_COUNTRIES:
            return False
        tokens = re.findall(r"\b[a-z]+\b", normalized)
        if not 1 <= len(tokens) <= 3:
            return False
        if tokens[0] in {"i", "not", "maybe", "unknown", "uncertain", "khong", "chua"}:
            return False
        return True

    def _looks_like_origin_answer(self, normalized: str) -> bool:
        return bool(
            re.fullmatch(
                r"(?:i(?:\s+am|'m)|im|i\s+come)\s+from\s+[^.!?]+[.!?]?",
                normalized,
            )
            or re.fullmatch(
                r"(?:my\s+country\s+is|toi\s+den\s+tu)\s+[^.!?]+[.!?]?",
                normalized,
            )
        )

    def _merge_pending_trip_details(
        self,
        pending_question: str,
        current_question: str,
        pending_intent: str | None,
    ) -> str:
        if pending_intent != "trip_planning":
            return pending_question

        details = self._without_passport_only_sentences(current_question)
        normalized_details = self._normalize(details)
        if not details or not self._has_additional_trip_details(normalized_details):
            return pending_question

        if self._is_complete_trip_request(normalized_details):
            return details
        if normalized_details in self._normalize(pending_question):
            return pending_question
        return f"{pending_question}\nAdditional trip details: {details}"

    def _without_passport_only_sentences(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", text.strip())
        trip_sentences = []
        for sentence in sentences:
            normalized = self._normalize(sentence)
            if not normalized:
                continue
            has_trip_details = self._has_additional_trip_details(normalized)
            if (
                self._contains_phrase(
                    normalized,
                    {"passport", "passports", "ho chieu"},
                )
                and not has_trip_details
            ):
                continue
            if self._looks_like_origin_answer(normalized) and not has_trip_details:
                continue
            trip_sentences.append(sentence.strip())
        return " ".join(trip_sentences).strip()

    def _has_additional_trip_details(self, normalized: str) -> bool:
        detail_phrases = {
            "budget",
            "ngan sach",
            "vnd",
            "million",
            "trieu",
            "start date",
            "starting",
            "bat dau",
            "focused on",
            "interested in",
            "interest",
            "so thich",
            "sightseeing",
            "dining",
            "am thuc",
        }
        return bool(
            self._contains_phrase(normalized, detail_phrases)
            or re.search(
                r"\b\d+\s*[- ]?\s*(day|days|night|nights|ngay|dem)\b",
                normalized,
            )
            or re.search(r"\b20\d{2}-\d{2}-\d{2}\b", normalized)
        )

    def _is_complete_trip_request(self, normalized: str) -> bool:
        has_destination = self._contains_phrase(normalized, _DESTINATION_PHRASES)
        has_duration = bool(
            re.search(r"\b\d+\s*[- ]?\s*(day|days|ngay)\b", normalized)
        )
        return has_destination and has_duration

    def _is_ambiguous_korea(self, normalized: str) -> bool:
        if not self._contains_phrase(normalized, {"korea"}):
            return False
        specific_names = {
            "south korea",
            "north korea",
            "republic of korea",
            "korea republic",
            "democratic peoples republic of korea",
        }
        return not self._contains_phrase(normalized, specific_names)

    def _as_bool(self, value) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes"}

    def _detect_supported_language(self, original: str, normalized: str) -> str:
        has_vietnamese_chars = bool(
            re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩị"
                      r"óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", original.lower())
        )
        has_english_marker = self._contains_phrase(
            normalized,
            _ENGLISH_LANGUAGE_MARKERS,
        )
        has_english_structure = self._contains_phrase(
            normalized,
            _ENGLISH_STRUCTURE_MARKERS,
        )
        has_vietnamese_marker = self._contains_phrase(
            normalized,
            _VIETNAMESE_LANGUAGE_PHRASES,
        )

        if has_vietnamese_chars:
            return "vi"
        if has_vietnamese_marker and has_english_structure:
            return "mixed"
        if has_vietnamese_marker:
            return "vi"
        if has_english_marker:
            return "en"
        if any(
            char.isalpha() and not ("a" <= char <= "z")
            for char in normalized
        ):
            return "unsupported"
        if len(re.findall(r"\b[a-z]+\b", normalized)) >= 3:
            return "unsupported"
        return "unknown"

    def _history_to_text(self, history: list) -> str:
        parts = []
        for message in history:
            content = str(getattr(message, "content", "")).strip()
            if not content:
                continue

            class_name = message.__class__.__name__.lower()
            if "human" in class_name:
                role = "USER"
            elif "ai" in class_name:
                role = "ASSISTANT"
            else:
                role = str(getattr(message, "role", "MESSAGE")).upper()
            parts.append(f"{role}: {content[:600]}")
        return "\n".join(parts)

    def _is_small_talk_only(self, text: str) -> bool:
        cleaned = re.sub(r"[^\w\s]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned in _SMALL_TALK_PHRASES

    def _contains_phrase(self, text: str, phrases: set[str]) -> bool:
        for phrase in phrases:
            pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            if re.search(pattern, text):
                return True
        return False

    def _reply(self, reply_type: str, language: str) -> str:
        replies = {
            "empty": {
                "vi": "Vui lòng nhập điểm đến hoặc nhu cầu du lịch cần tư vấn.",
                "en": "Please enter a Vietnam destination or travel question.",
            },
            "small_talk": {
                "vi": "Xin chào, hãy nhập điểm đến hoặc nhu cầu du lịch cần tư vấn.",
                "en": "Hello. Tell me which destination in Vietnam you would like help with.",
            },
            "not_travel": {
                "vi": "Hệ thống hiện chỉ hỗ trợ tư vấn du lịch tại Việt Nam.",
                "en": "This service currently supports travel advice for Vietnam only.",
            },
            "uncertain": {
                "vi": "Vui lòng cho biết điểm đến tại Việt Nam và bạn cần gợi ý địa điểm hay lập lịch trình. Để tư vấn phù hợp hơn, hãy bổ sung thời lượng, sở thích, ngân sách, ngày bắt đầu và quốc gia cấp hộ chiếu sẽ sử dụng. Ví dụ: Tôi muốn đi Hà Nội 2 ngày 1 đêm, ưu tiên tham quan và ẩm thực, ngân sách 5 triệu VND, bắt đầu ngày 2026-07-19 và sử dụng hộ chiếu Trung Quốc.",
                "en": "Please provide the Vietnam destination and whether you need recommendations or an itinerary. For a better result, include duration, interests, budget, start date, and the passport country you will use. Example: I would like to visit Hanoi for a 2-day, 1-night trip focused on sightseeing and dining, with a budget of 5 million VND, starting on July 19, 2026, and I will use a Chinese passport.",
            },
            "ask_country": {
                "vi": "Bạn sẽ sử dụng hộ chiếu do quốc gia nào cấp để nhập cảnh Việt Nam? Nếu có nhiều hộ chiếu, vui lòng chọn hộ chiếu dự định sử dụng.",
                "en": "Which country's passport will you use to enter Vietnam? If you hold multiple passports, please specify the one you plan to use.",
            },
            "ask_country_plan": {
                "vi": "Bạn sẽ sử dụng hộ chiếu do quốc gia nào cấp để nhập cảnh Việt Nam? Để lịch trình phù hợp hơn, bạn cũng có thể cung cấp sở thích, ngân sách và ngày bắt đầu. Ví dụ: Tôi sử dụng hộ chiếu Trung Quốc. Tôi muốn đi Hà Nội 2 ngày 1 đêm, ưu tiên tham quan và ẩm thực, ngân sách 5 triệu VND, bắt đầu ngày 2026-07-19.",
                "en": "Which country's passport will you use to enter Vietnam? For a better itinerary, you can also provide your interests, budget, and start date. Example: I will use a Chinese passport. I would like to visit Hanoi for a 2-day, 1-night trip focused on sightseeing and dining, with a budget of 5 million VND, starting on July 19, 2026.",
            },
            "clarify_korea": {
                "vi": "Hộ chiếu được cấp bởi Hàn Quốc (Republic of Korea) hay Triều Tiên (DPRK)? Vui lòng chọn đúng quốc gia được ghi trên hộ chiếu.",
                "en": "Was the passport issued by South Korea (Republic of Korea) or North Korea (DPRK)? Please specify the country shown on the passport.",
            },
            "unsupported": {
                "vi": "Hiện hệ thống chỉ hỗ trợ tiếng Việt và tiếng Anh. This service currently supports Vietnamese and English only.",
                "en": "This service currently supports Vietnamese and English only. Hiện hệ thống chỉ hỗ trợ tiếng Việt và tiếng Anh.",
            },
        }
        return replies[reply_type][language if language in {"vi", "en"} else "vi"]

    def _fast_reply(
        self,
        intent: str,
        reply: str,
        confidence: float,
        reason: str,
        language: str,
        response_language: str,
        passport_country: str | None = None,
        resolved_question: str | None = None,
        stay_days: int | None = None,
        entry_date: str | None = None,
    ) -> RouteDecision:
        return RouteDecision(
            intent=intent,
            action="fast_reply",
            confidence=confidence,
            reply=reply,
            reason=reason,
            language=language,
            response_language=response_language,
            passport_country=passport_country,
            resolved_question=resolved_question,
            stay_days=stay_days,
            entry_date=entry_date,
        )

    def _normalize(self, text: str) -> str:
        text = str(text or "").lower()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = text.replace("đ", "d")
        return re.sub(r"\s+", " ", text).strip()

    def _confidence(self, data: dict) -> float:
        try:
            confidence = float(data.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        return min(max(confidence, 0.0), 1.0)

    def _optional_positive_int(self, value) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _optional_text(self, value) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _parse_json(self, text: str) -> dict:
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean = "\n".join(lines).strip()

        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Classifier response does not contain JSON object")

        data = json.loads(clean[start : end + 1])
        if not isinstance(data, dict):
            raise ValueError("Classifier JSON must be an object")
        return data
