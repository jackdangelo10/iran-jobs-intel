from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from deep_translator import GoogleTranslator

from src.database import IranJobsDB
from src.utils.sha256_hash import sha256_hash

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persian digit map for salary/number parsing
# ---------------------------------------------------------------------------
_FA_DIGIT = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


@dataclass
class ProcessorStats:
    total: int = 0
    processed: int = 0
    failed: int = 0
    translated_title: int = 0
    translated_description: int = 0
    companies_linked: int = 0
    locations_linked: int = 0
    skills_linked: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "total": self.total,
            "processed": self.processed,
            "failed": self.failed,
            "translated_title": self.translated_title,
            "translated_description": self.translated_description,
            "companies_linked": self.companies_linked,
            "locations_linked": self.locations_linked,
            "skills_linked": self.skills_linked,
        }


class JobProcessor:
    """Full processing pipeline for pending job postings."""

    # ------------------------------------------------------------------
    # Comprehensive skill dictionary (canonical → list of match strings)
    # ------------------------------------------------------------------
    SKILL_PATTERNS: dict[str, list[str]] = {
        # ── Languages ──────────────────────────────────────────────────
        "Python":           ["python", "پایتون"],
        "JavaScript":       ["javascript", "js", "جاوااسکریپت"],
        "TypeScript":       ["typescript", "ts", "تایپ‌اسکریپت", "تایپ اسکریپت"],
        "Java":             ["java", "جاوا"],
        "C#":               ["c#", "csharp", "c sharp", "سی‌شارپ", "سی شارپ"],
        "C++":              ["c++", "cpp", "سی‌پلاس‌پلاس"],
        "C":                [" c ", "language c", "زبان c"],
        "Go":               ["golang", " go ", "گولنگ"],
        "Rust":             ["rust", "راست"],
        "PHP":              ["php"],
        "Ruby":             ["ruby", "روبی"],
        "Swift":            ["swift"],
        "Kotlin":           ["kotlin"],
        "Scala":            ["scala"],
        "R":                [" r ", "r programming", "r language", "آر"],
        "MATLAB":           ["matlab", "متلب"],
        "Dart":             ["dart", "flutter/dart"],
        "Shell":            ["bash", "shell script", "powershell", "bash scripting"],
        "Perl":             ["perl"],
        "VBA":              ["vba", "visual basic"],
        "Assembly":         ["assembly", "asm", "اسمبلی"],

        # ── Web Front-end ───────────────────────────────────────────────
        "HTML":             ["html", "html5"],
        "CSS":              ["css", "css3"],
        "React":            ["react", "reactjs", "react.js", "ری‌اکت", "ری اکت"],
        "Vue.js":           ["vue", "vuejs", "vue.js", "ویو"],
        "Angular":          ["angular", "angularjs", "انگولار"],
        "Next.js":          ["next.js", "nextjs"],
        "Nuxt.js":          ["nuxt.js", "nuxtjs"],
        "Svelte":           ["svelte"],
        "jQuery":           ["jquery"],
        "Bootstrap":        ["bootstrap"],
        "Tailwind CSS":     ["tailwind", "tailwindcss"],
        "Webpack":          ["webpack"],
        "Vite":             ["vite"],

        # ── Web Back-end ────────────────────────────────────────────────
        "Node.js":          ["node.js", "nodejs", "node js"],
        "Express.js":       ["express.js", "expressjs", "express js"],
        "Django":           ["django", "جنگو"],
        "Flask":            ["flask"],
        "FastAPI":          ["fastapi", "fast api"],
        "Spring Boot":      ["spring boot", "spring", "springframework"],
        "Laravel":          ["laravel"],
        "Rails":            ["rails", "ruby on rails"],
        "ASP.NET":          ["asp.net", "aspnet", ".net", "dotnet"],
        "NestJS":           ["nestjs", "nest.js"],

        # ── Mobile ──────────────────────────────────────────────────────
        "React Native":     ["react native"],
        "Flutter":          ["flutter"],
        "Android":          ["android"],
        "iOS":              ["ios", "xcode"],

        # ── Databases ───────────────────────────────────────────────────
        "SQL":              [" sql ", "sql query", "sql queries", "اس‌کیو‌ال"],
        "PostgreSQL":       ["postgresql", "postgres"],
        "MySQL":            ["mysql"],
        "SQLite":           ["sqlite"],
        "SQL Server":       ["sql server", "mssql", "t-sql"],
        "Oracle":           ["oracle database", "oracle db", "pl/sql", "plsql"],
        "MongoDB":          ["mongodb", "mongo"],
        "Redis":            ["redis"],
        "Elasticsearch":    ["elasticsearch", "elastic search"],
        "Cassandra":        ["cassandra"],
        "ClickHouse":       ["clickhouse", "click house"],
        "DynamoDB":         ["dynamodb"],
        "Neo4j":            ["neo4j", "graph database"],
        "InfluxDB":         ["influxdb"],

        # ── Messaging / Queues ──────────────────────────────────────────
        "Kafka":            ["kafka", "apache kafka"],
        "RabbitMQ":         ["rabbitmq", "rabbit mq"],
        "Celery":           ["celery"],
        "NATS":             ["nats"],
        "ZeroMQ":           ["zeromq", "zmq"],

        # ── DevOps / Infra ──────────────────────────────────────────────
        "Docker":           ["docker", "داکر"],
        "Kubernetes":       ["kubernetes", "k8s", "کوبرنتیز"],
        "Linux":            ["linux", "ubuntu", "centos", "debian", "لینوکس"],
        "Git":              ["git", "گیت"],
        "GitHub":           ["github"],
        "GitLab":           ["gitlab"],
        "CI/CD":            ["ci/cd", "cicd", "continuous integration", "continuous delivery"],
        "Jenkins":          ["jenkins"],
        "GitHub Actions":   ["github actions"],
        "GitLab CI":        ["gitlab ci", "gitlab-ci"],
        "Terraform":        ["terraform"],
        "Ansible":          ["ansible"],
        "Helm":             ["helm chart", " helm "],
        "Nginx":            ["nginx"],
        "Apache":           ["apache httpd", "apache server"],
        "Prometheus":       ["prometheus"],
        "Grafana":          ["grafana"],
        "ELK Stack":        ["elk stack", "kibana", "logstash"],
        "Vault":            ["hashicorp vault"],

        # ── Cloud ───────────────────────────────────────────────────────
        "AWS":              ["aws", "amazon web services"],
        "GCP":              ["gcp", "google cloud", "google cloud platform"],
        "Azure":            ["azure", "microsoft azure"],
        "DigitalOcean":     ["digitalocean", "digital ocean"],

        # ── ML / AI / Data ──────────────────────────────────────────────
        "Machine Learning": ["machine learning", "ml ", "یادگیری ماشین"],
        "Deep Learning":    ["deep learning", "یادگیری عمیق"],
        "NLP":              ["nlp", "natural language processing", "پردازش زبان"],
        "Computer Vision":  ["computer vision", "بینایی ماشین"],
        "TensorFlow":       ["tensorflow", "tf2"],
        "PyTorch":          ["pytorch", "torch"],
        "Keras":            ["keras"],
        "Scikit-learn":     ["scikit-learn", "sklearn"],
        "Pandas":           ["pandas", "پانداس"],
        "NumPy":            ["numpy"],
        "SciPy":            ["scipy"],
        "OpenCV":           ["opencv", "open cv"],
        "Hugging Face":     ["hugging face", "huggingface", "transformers"],
        "XGBoost":          ["xgboost"],
        "LightGBM":         ["lightgbm"],
        "Data Analysis":    ["data analysis", "تحلیل داده", "data analytics"],
        "Data Engineering": ["data engineering", "data pipeline", "etl", "مهندسی داده"],
        "Spark":            ["apache spark", "pyspark"],
        "Hadoop":           ["hadoop", "hdfs"],
        "Airflow":          ["airflow", "apache airflow"],
        "dbt":              [" dbt ", "data build tool"],

        # ── BI / Visualization ──────────────────────────────────────────
        "Power BI":         ["power bi", "powerbi"],
        "Tableau":          ["tableau"],
        "Looker":           ["looker"],
        "Excel":            ["excel", "اکسل"],
        "SPSS":             ["spss"],

        # ── API / Architecture ──────────────────────────────────────────
        "REST API":         ["rest api", "restful", "rest ful"],
        "GraphQL":          ["graphql"],
        "gRPC":             ["grpc"],
        "WebSocket":        ["websocket", "web socket"],
        "Microservices":    ["microservices", "microservice", "میکروسرویس"],
        "OAuth":            ["oauth", "oauth2"],
        "JWT":              ["jwt", "json web token"],

        # ── Methodology ─────────────────────────────────────────────────
        "Agile":            ["agile", "اجایل"],
        "Scrum":            ["scrum", "اسکرام"],
        "Jira":             ["jira"],
        "Figma":            ["figma"],

        # ── Other / Domain ──────────────────────────────────────────────
        "Blockchain":       ["blockchain", "بلاک‌چین", "solidity", "web3"],
        "Unity":            ["unity3d", "unity engine", " unity "],
        "Unreal Engine":    ["unreal engine", "unreal"],
        "AutoCAD":          ["autocad"],
        "SAP":              ["sap erp", " sap "],
        "Photoshop":        ["photoshop"],
        "SEO":              [" seo ", "search engine optimization"],
        "WordPress":        ["wordpress"],
    }

    # ------------------------------------------------------------------
    # Employment type normalisation map (raw → canonical)
    # ------------------------------------------------------------------
    _EMP_TYPE_MAP: dict[str, str] = {
        # Full time
        "full_time": "full_time", "full-time": "full_time",
        "full time": "full_time", "تمام وقت": "full_time",
        "تمام‌وقت": "full_time", "فول تایم": "full_time",
        "تمام‌ وقت": "full_time",
        # Part time
        "part_time": "part_time", "part-time": "part_time",
        "part time": "part_time", "نیمه وقت": "part_time",
        "نیمه‌وقت": "part_time", "پاره وقت": "part_time",
        # Remote
        "remote": "remote", "دورکاری": "remote",
        "remote work": "remote", "کاملاً دورکار": "remote",
        # Hybrid
        "hybrid": "hybrid", "هیبریدی": "hybrid", "hybrid work": "hybrid",
        # Contract / project-based
        "contract": "contract", "قراردادی": "contract",
        "پروژه‌ای": "contract", "پروژه ای": "contract",
        "project_based": "contract",
        # Freelance
        "freelance": "freelance", "فریلنسر": "freelance",
        "freelancer": "freelance",
        # Internship
        "internship": "internship", "کارآموزی": "internship",
        "کارآموز": "internship", "intern": "internship",
        "trainee": "internship",
    }

    # ------------------------------------------------------------------
    # Experience level normalisation map (raw → canonical)
    # ------------------------------------------------------------------
    _EXP_LEVEL_MAP: dict[str, str] = {
        # Entry / junior
        "entry_level": "entry_level", "entry level": "entry_level",
        "junior": "entry_level", "entry": "entry_level",
        "تازه‌کار": "entry_level", "بدون سابقه": "entry_level",
        "کم‌تجربه": "entry_level", "جونیور": "entry_level",
        "less than 1 year": "entry_level", "زیر یک سال": "entry_level",
        # Mid level
        "mid_level": "mid_level", "mid level": "mid_level",
        "mid": "mid_level", "intermediate": "mid_level",
        "با تجربه": "mid_level", "کارشناس": "mid_level",
        "1-3 years": "mid_level", "2-4 years": "mid_level",
        "3-5 years": "mid_level",
        # Senior
        "senior": "senior", "ارشد": "senior",
        "سینیور": "senior", "senior level": "senior",
        "5+ years": "senior", "بیش از ۵ سال": "senior",
        # Lead
        "lead": "lead", "تیم‌لید": "lead",
        "team lead": "lead", "tech lead": "lead",
        # Manager / executive
        "manager": "manager", "مدیر": "manager",
        "director": "manager", "head of": "manager",
        "مدیریت": "manager",
        # Expert / principal
        "expert": "expert", "خبره": "expert",
        "principal": "expert", "staff": "expert",
    }

    def __init__(self, db: IranJobsDB):
        self.db = db
        self.conn = db.db_connection
        self._translator: GoogleTranslator | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, batch_size: int = 200, dry_run: bool = False) -> dict[str, Any]:
        pending = self._get_pending_jobs(limit=batch_size)
        stats = ProcessorStats(total=len(pending))

        if dry_run:
            logger.info("Dry run enabled - processor will not write to database")
            return {
                "status": "dry_run",
                "batch_size": batch_size,
                "pending_jobs_found": len(pending),
                "stats": stats.as_dict(),
            }

        if not pending:
            return {
                "status": "completed",
                "batch_size": batch_size,
                "pending_jobs_found": 0,
                "stats": stats.as_dict(),
            }

        process_id = os.getenv("IRAN_JOBS_PROCESS_ID", "processor_mvp")
        self._log_processing_event(
            process_type="processing",
            process_id=process_id,
            status="started",
            message=f"Starting processor batch of {len(pending)} jobs",
            records_processed=0,
            records_failed=0,
        )

        for row in pending:
            job_id = int(row["id"])
            try:
                title_fa   = (row.get("title_persian") or "").strip()
                desc_fa    = (row.get("description_persian") or "").strip()
                company_raw = (row.get("company_name_raw") or "").strip()
                location_raw = (row.get("location_raw") or "").strip()
                emp_type_raw  = (row.get("employment_type") or "unknown").strip()
                exp_level_raw = (row.get("experience_level") or "unknown").strip()
                skills_json_raw = row.get("skills_required_json")

                # Translation
                title_en = self._translate_cached(title_fa) if title_fa else None
                desc_en  = self._translate_cached(desc_fa)  if desc_fa  else None
                title_norm = self._normalize_text(title_en or title_fa) or None

                if title_en:
                    stats.translated_title += 1
                if desc_en:
                    stats.translated_description += 1

                # Normalise employment / experience fields
                emp_type  = self._normalize_employment_type(emp_type_raw)
                exp_level = self._normalize_experience_level(exp_level_raw)

                # Salary parsing (from description if not structured)
                salary_min, salary_max = self._parse_salary_from_text(
                    row.get("salary_min_original"),
                    desc_fa,
                )

                # Entity resolution
                company_id  = self._upsert_company(company_raw)  if company_raw  else None
                location_id = self._upsert_location(location_raw) if location_raw else None

                if company_id:
                    stats.companies_linked += 1
                if location_id:
                    stats.locations_linked += 1

                # Skill extraction — text matching + pre-extracted tags from scrapers
                search_text = " ".join([title_fa, desc_fa, title_en or "", desc_en or ""])
                skills = self._extract_skills(search_text)

                # Merge in skills already extracted by the scraper (e.g. Jobinja tags)
                if skills_json_raw:
                    try:
                        pre = (
                            json.loads(skills_json_raw)
                            if isinstance(skills_json_raw, str)
                            else skills_json_raw
                        )
                        if isinstance(pre, list):
                            skills = sorted(set(skills + [s for s in pre if isinstance(s, str)]))
                    except Exception:
                        pass

                skill_ids = self._upsert_skills(skills)
                if skill_ids:
                    self._upsert_job_skills(job_id, skill_ids)
                    stats.skills_linked += len(skill_ids)

                quality = self._compute_data_quality(
                    title_en=title_en,
                    desc_en=desc_en,
                    company_id=company_id,
                    location_id=location_id,
                    skill_count=len(skill_ids),
                )

                self._mark_job_processed(
                    job_id=job_id,
                    title_en=title_en,
                    desc_en=desc_en,
                    title_normalized=title_norm,
                    company_id=company_id,
                    location_id=location_id,
                    skills=skills,
                    quality=quality,
                    employment_type=emp_type,
                    experience_level=exp_level,
                    salary_min=salary_min,
                    salary_max=salary_max,
                )
                stats.processed += 1

            except Exception as exc:
                logger.exception("Processor failed for job_id=%s", job_id)
                self._mark_job_failed(job_id, str(exc))
                stats.failed += 1

        final_status = "completed_with_errors" if stats.failed else "completed"
        self._log_processing_event(
            process_type="processing",
            process_id=process_id,
            status="completed" if stats.failed == 0 else "warning",
            message=f"Processor batch finished with status={final_status}",
            records_processed=stats.processed,
            records_failed=stats.failed,
            details_json=stats.as_dict(),
        )

        return {
            "status": final_status,
            "batch_size": batch_size,
            "pending_jobs_found": len(pending),
            "stats": stats.as_dict(),
        }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _get_pending_jobs(self, limit: int) -> list[dict[str, Any]]:
        return self.conn.fetchall(
            """
            SELECT id, title_persian, description_persian,
                   company_name_raw, location_raw,
                   employment_type, experience_level,
                   salary_min_original,
                   skills_required_json
            FROM iran_jobs.job_postings
            WHERE processing_status = 'pending'
            ORDER BY id ASC
            LIMIT %s
            """,
            (limit,),
        )

    def _translate_cached(self, text: str) -> str | None:
        clean = text.strip()
        if not clean:
            return None

        text_hash = sha256_hash(f"fa|en|{clean}")
        cached = self.conn.fetchone(
            "SELECT translated_text FROM iran_jobs.translation_cache WHERE source_text_hash = %s",
            (text_hash,),
        )
        if cached and cached.get("translated_text"):
            self.conn.execute_with_transaction(
                """
                UPDATE iran_jobs.translation_cache
                SET last_used_at = NOW(), usage_count = usage_count + 1
                WHERE source_text_hash = %s
                """,
                (text_hash,),
            )
            return str(cached["translated_text"])

        translated: str | None = None
        try:
            if self._translator is None:
                self._translator = GoogleTranslator(source="fa", target="en")
            translated = self._translator.translate(clean)
        except Exception:
            translated = clean

        self.conn.execute_with_transaction(
            """
            INSERT INTO iran_jobs.translation_cache (
                source_text_hash, source_text, source_language, target_language,
                translated_text, translation_service, translation_confidence,
                created_at, last_used_at, usage_count, is_verified, needs_review
            )
            VALUES (%s, %s, 'fa', 'en', %s, 'google', %s, NOW(), NOW(), 1, FALSE, FALSE)
            ON CONFLICT (source_text_hash) DO UPDATE
            SET translated_text = COALESCE(iran_jobs.translation_cache.translated_text,
                                            EXCLUDED.translated_text),
                last_used_at  = NOW(),
                usage_count   = iran_jobs.translation_cache.usage_count + 1
            """,
            (text_hash, clean, translated, 0.8 if translated else None),
        )
        return translated

    def _upsert_company(self, company_raw: str) -> int | None:
        canonical = self._canonical_company_name(company_raw)
        if not canonical:
            return None

        existing = self.conn.fetchone(
            "SELECT id FROM iran_jobs.companies WHERE canonical_name = %s",
            (canonical,),
        )
        if existing:
            company_id = int(existing["id"])
            self.conn.execute_with_transaction(
                """
                UPDATE iran_jobs.companies
                SET last_activity_date = CURRENT_DATE,
                    total_job_postings = total_job_postings + 1,
                    active_job_postings = active_job_postings + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (company_id,),
            )
            return company_id

        try:
            return self.conn.execute_insert_with_id(
                """
                INSERT INTO iran_jobs.companies (
                    display_name_persian, canonical_name,
                    first_seen_date, last_activity_date, is_active,
                    total_job_postings, active_job_postings
                )
                VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE, TRUE, 1, 1)
                RETURNING id
                """,
                (company_raw, canonical),
            )
        except Exception:
            fallback = self.conn.fetchone(
                "SELECT id FROM iran_jobs.companies WHERE canonical_name = %s",
                (canonical,),
            )
            return int(fallback["id"]) if fallback else None

    def _upsert_location(self, location_raw: str) -> int | None:
        norm = self._normalize_text(location_raw)
        if not norm:
            return None

        existing = self.conn.fetchone(
            "SELECT id FROM iran_jobs.locations WHERE location_normalized = %s",
            (norm,),
        )
        if existing:
            return int(existing["id"])

        try:
            return self.conn.execute_insert_with_id(
                """
                INSERT INTO iran_jobs.locations (
                    city_persian, location_normalized, location_type
                )
                VALUES (%s, %s, 'city')
                RETURNING id
                """,
                (location_raw, norm),
            )
        except Exception:
            fallback = self.conn.fetchone(
                "SELECT id FROM iran_jobs.locations WHERE location_normalized = %s",
                (norm,),
            )
            return int(fallback["id"]) if fallback else None

    def _upsert_skills(self, skill_names: list[str]) -> list[int]:
        skill_ids: list[int] = []
        for skill_name in skill_names:
            existing = self.conn.fetchone(
                "SELECT id FROM iran_jobs.skills WHERE skill_name_english = %s",
                (skill_name,),
            )
            if existing:
                skill_id = int(existing["id"])
                self.conn.execute_with_transaction(
                    """
                    UPDATE iran_jobs.skills
                    SET last_seen_date = CURRENT_DATE, is_active = TRUE, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (skill_id,),
                )
                skill_ids.append(skill_id)
                continue

            try:
                skill_id = self.conn.execute_insert_with_id(
                    """
                    INSERT INTO iran_jobs.skills (
                        skill_name_english, skill_category, first_seen_date, last_seen_date, is_active
                    )
                    VALUES (%s, 'technical', CURRENT_DATE, CURRENT_DATE, TRUE)
                    RETURNING id
                    """,
                    (skill_name,),
                )
                skill_ids.append(skill_id)
            except Exception:
                fallback = self.conn.fetchone(
                    "SELECT id FROM iran_jobs.skills WHERE skill_name_english = %s",
                    (skill_name,),
                )
                if fallback:
                    skill_ids.append(int(fallback["id"]))
        return skill_ids

    def _upsert_job_skills(self, job_id: int, skill_ids: list[int]) -> None:
        for skill_id in skill_ids:
            self.conn.execute_with_transaction(
                """
                INSERT INTO iran_jobs.job_skills (
                    job_posting_id, skill_id, requirement_type, proficiency_level,
                    confidence_score, extraction_method, verified, needs_review, created_at
                )
                VALUES (%s, %s, 'mentioned', 'unknown', 0.7, 'keyword_match', FALSE, FALSE, NOW())
                ON CONFLICT (job_posting_id, skill_id) DO UPDATE
                SET confidence_score = GREATEST(iran_jobs.job_skills.confidence_score,
                                                 EXCLUDED.confidence_score),
                    needs_review = FALSE
                """,
                (job_id, skill_id),
            )

    def _mark_job_processed(
        self,
        job_id: int,
        title_en: str | None,
        desc_en: str | None,
        title_normalized: str | None,
        company_id: int | None,
        location_id: int | None,
        skills: list[str],
        quality: float,
        employment_type: str = "unknown",
        experience_level: str = "unknown",
        salary_min: float | None = None,
        salary_max: float | None = None,
    ) -> None:
        self.conn.execute_with_transaction(
            """
            UPDATE iran_jobs.job_postings
            SET title_english              = %s,
                description_english        = %s,
                title_normalized           = %s,
                company_id                 = %s,
                location_id                = %s,
                employment_type            = CASE WHEN %s != 'unknown' THEN %s
                                                  ELSE employment_type END,
                experience_level           = CASE WHEN %s != 'unknown' THEN %s
                                                  ELSE experience_level END,
                salary_min_original        = COALESCE(%s, salary_min_original),
                salary_max_original        = COALESCE(%s, salary_max_original),
                technologies_mentioned_json = %s,
                data_quality_score         = %s,
                processing_confidence      = %s,
                processing_status          = 'processed'
            WHERE id = %s
            """,
            (
                title_en,
                desc_en,
                title_normalized,
                company_id,
                location_id,
                employment_type, employment_type,
                experience_level, experience_level,
                salary_min,
                salary_max,
                json.dumps(skills, ensure_ascii=False) if skills else None,
                quality,
                min(1.0, quality + 0.1),
                job_id,
            ),
        )

    def _mark_job_failed(self, job_id: int, error_message: str) -> None:
        self.conn.execute_with_transaction(
            """
            UPDATE iran_jobs.job_postings
            SET processing_status = 'failed',
                manual_review_needed = TRUE
            WHERE id = %s
            """,
            (job_id,),
        )
        self._log_processing_event(
            process_type="processing",
            process_id="processor_mvp",
            status="failed",
            message=f"Failed processing job_posting id={job_id}",
            entity_type="job_posting",
            entity_id=job_id,
            error_details=error_message[:2000],
            records_processed=0,
            records_failed=1,
        )

    def _log_processing_event(
        self,
        process_type: str,
        process_id: str,
        status: str,
        message: str,
        records_processed: int,
        records_failed: int,
        entity_type: str | None = None,
        entity_id: int | None = None,
        error_details: str | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        self.conn.execute_with_transaction(
            """
            INSERT INTO iran_jobs.processing_logs (
                process_type, process_id, entity_type, entity_id, status, message,
                details_json, records_processed, records_failed, error_details, timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                process_type,
                process_id,
                entity_type,
                entity_id,
                status,
                message,
                json.dumps(details_json) if details_json else None,
                records_processed,
                records_failed,
                error_details,
            ),
        )

    # ------------------------------------------------------------------
    # Pure-function helpers
    # ------------------------------------------------------------------

    def _extract_skills(self, text: str) -> list[str]:
        if not text:
            return []
        lowered = text.lower()
        found: list[str] = []
        for canonical, patterns in self.SKILL_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in lowered:
                    found.append(canonical)
                    break
        return sorted(set(found))

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = text.lower().strip()
        lowered = re.sub(r"\s+", " ", lowered)
        lowered = re.sub(r"[^\w\s\-]+", "", lowered)
        return lowered.strip()

    @staticmethod
    def _canonical_company_name(name: str) -> str:
        value = JobProcessor._normalize_text(name)
        value = value.replace("شرکت ", "").strip()
        return value

    @classmethod
    def _normalize_employment_type(cls, raw: str) -> str:
        """Map a raw employment_type string to a canonical value."""
        if not raw or raw.lower() in ("unknown", ""):
            return "unknown"
        key = raw.strip().lower()
        # Direct lookup
        if key in cls._EMP_TYPE_MAP:
            return cls._EMP_TYPE_MAP[key]
        # Substring scan (handles long phrases)
        for token, canonical in cls._EMP_TYPE_MAP.items():
            if token in key:
                return canonical
        return "unknown"

    @classmethod
    def _normalize_experience_level(cls, raw: str) -> str:
        """Map a raw experience_level string to a canonical value."""
        if not raw or raw.lower() in ("unknown", ""):
            return "unknown"
        key = raw.strip().lower()
        if key in cls._EXP_LEVEL_MAP:
            return cls._EXP_LEVEL_MAP[key]
        for token, canonical in cls._EXP_LEVEL_MAP.items():
            if token in key:
                return canonical
        return "unknown"

    @staticmethod
    def _parse_salary_from_text(
        existing_min: Any,
        description: str,
    ) -> tuple[float | None, float | None]:
        """
        Try to extract salary figures from Persian job description text.

        Handles patterns like:
          "۱,۵۰۰,۰۰۰ تومان"          → single value
          "از ۱,۰۰۰,۰۰۰ تا ۲,۰۰۰,۰۰۰ تومان"  → range
          "حقوق توافقی"               → negotiable, skip

        Returns (min_toman, max_toman) or (None, None).
        Toman stored as-is (salary_currency_original = 'IRR' but we pass raw Toman).
        """
        if existing_min is not None:
            # Already parsed by the scraper
            return None, None
        if not description:
            return None, None

        text = description.translate(_FA_DIGIT)

        # Range pattern: "از X تا Y تومان" or "X تا Y تومان"
        range_pat = re.search(
            r"(?:از\s*)?([\d,]+)\s*تا\s*([\d,]+)\s*(?:تومان|ریال)",
            text,
        )
        if range_pat:
            try:
                lo = float(range_pat.group(1).replace(",", ""))
                hi = float(range_pat.group(2).replace(",", ""))
                return lo, hi
            except ValueError:
                pass

        # Single value pattern: "X تومان"
        single_pat = re.search(r"([\d,]{5,})\s*(?:تومان|ریال)", text)
        if single_pat:
            try:
                val = float(single_pat.group(1).replace(",", ""))
                return val, None
            except ValueError:
                pass

        return None, None

    @staticmethod
    def _compute_data_quality(
        title_en: str | None,
        desc_en: str | None,
        company_id: int | None,
        location_id: int | None,
        skill_count: int,
    ) -> float:
        score = 0.0
        if title_en:
            score += 0.30
        if desc_en:
            score += 0.25
        if company_id:
            score += 0.20
        if location_id:
            score += 0.15
        if skill_count > 0:
            score += 0.10
        return round(min(score, 1.0), 3)
