"""Tests for data models."""
import pytest
from app.models.student import (
    StudentProfile, Education, AcademicBackground,
    EnglishLanguage, WorkExperience, ResearchExperience,
    Publication, Project,
)
from app.models.requirements import (
    UniversityRequirements, CourseRequirement,
    AcademicRequirement, EnglishRequirement,
)
from app.models.assessment import (
    AssessmentResult, AssessmentCategory, DocumentConsistency,
    StudentSummary, TargetInfo, EligibilityStatus,
    CategoryStatus, ConfidenceLevel,
)


class TestStudentModels:
    def test_education_model(self):
        edu = Education(
            qualification="B.Tech",
            field="Computer Science",
            institution="Example University",
            score="78%",
            completion_year=2025,
        )
        
        assert edu.qualification == "B.Tech"
        assert edu.field == "Computer Science"
        assert edu.score == "78%"

    def test_education_optional_fields(self):
        edu = Education(
            qualification="MSc",
            field="AI",
            institution="Test Uni",
        )
        
        assert edu.score is None
        assert edu.completion_year is None

    def test_academic_background_model(self):
        bg = AcademicBackground(
            primary_field="Computer Science",
            subjects=["Programming", "Algorithms"],
        )
        
        assert bg.primary_field == "Computer Science"
        assert len(bg.subjects) == 2

    def test_english_language_model(self):
        eng = EnglishLanguage(
            test="IELTS",
            overall="7.0",
            components={"listening": "7.0", "reading": "7.5"},
        )
        
        assert eng.test == "IELTS"
        assert eng.overall == "7.0"
        assert eng.components["listening"] == "7.0"

    def test_student_profile_model(self):
        profile = StudentProfile(
            nationality="India",
            education=[
                Education(
                    qualification="B.Tech",
                    field="CS",
                    institution="Uni",
                    score="78%",
                    completion_year=2025,
                )
            ],
        )
        
        assert profile.nationality == "India"
        assert len(profile.education) == 1
        assert profile.education[0].qualification == "B.Tech"


class TestRequirementModels:
    def test_academic_requirement_model(self):
        req = AcademicRequirement(
            required_degree="Bachelor's",
            required_degree_duration="4 years",
            required_field="CS",
            minimum_score="60%",
            required_classification="2:1",
            prerequisite_subjects=["Math", "Programming"],
            country_specific_equivalency="Indian 4-year degree 60%+",
        )
        
        assert req.required_degree == "Bachelor's"
        assert len(req.prerequisite_subjects) == 2

    def test_english_requirement_model(self):
        req = EnglishRequirement(
            accepted_tests=["IELTS", "TOEFL"],
            minimum_overall="6.5",
            minimum_components={"listening": "6.0"},
            country_exemptions=["USA"],
            degree_country_exemptions=["UK"],
        )
        
        assert "IELTS" in req.accepted_tests
        assert req.minimum_overall == "6.5"

    def test_course_requirement_model(self):
        course = CourseRequirement(
            course_name="MSc AI",
            program_type="Taught",
            academic=AcademicRequirement(required_degree="Bachelor's"),
            english=EnglishRequirement(accepted_tests=["IELTS"], minimum_overall="6.5"),
            research_proposal_required=False,
        )
        
        assert course.course_name == "MSc AI"
        assert course.research_proposal_required is False

    def test_university_requirements_model(self):
        uni = UniversityRequirements(
            university="Test University",
            country="UK",
            courses=[
                CourseRequirement(
                    course_name="MSc AI",
                    program_type="Taught",
                    academic=AcademicRequirement(required_degree="Bachelor's"),
                    english=EnglishRequirement(accepted_tests=["IELTS"], minimum_overall="6.5"),
                )
            ],
            india_specific="Indian 4-year degree 60%+",
            source_urls=["https://example.com"],
        )
        
        assert uni.university == "Test University"
        assert len(uni.courses) == 1
        assert uni.india_specific is not None


class TestAssessmentModels:
    def test_assessment_category_model(self):
        cat = AssessmentCategory(
            category="Academic Qualification",
            status=CategoryStatus.PASS,
            requirement="Bachelor's degree",
            student_value="B.Tech CS",
            reason="Relevant degree",
            source="University website",
            confidence=ConfidenceLevel.HIGH,
        )
        
        assert cat.category == "Academic Qualification"
        assert cat.status == CategoryStatus.PASS
        assert cat.confidence == ConfidenceLevel.HIGH

    def test_document_consistency_model(self):
        dc = DocumentConsistency(
            status=CategoryStatus.PASS,
            issues=[],
        )
        
        assert dc.status == CategoryStatus.PASS
        assert dc.issues == []

    def test_document_consistency_with_issues(self):
        dc = DocumentConsistency(
            status=CategoryStatus.REQUIRES_VERIFICATION,
            issues=["Conflicting graduation years"],
        )
        
        assert dc.status == CategoryStatus.REQUIRES_VERIFICATION
        assert len(dc.issues) == 1

    def test_student_summary_model(self):
        summary = StudentSummary(
            nationality="India",
            highest_qualification="B.Tech CS",
            academic_score="78%",
        )
        
        assert summary.nationality == "India"
        assert summary.highest_qualification == "B.Tech CS"

    def test_target_info_model(self):
        target = TargetInfo(
            university="Test Uni",
            country="UK",
            course="MSc AI",
            degree_level="Masters",
        )
        
        assert target.university == "Test Uni"
        assert target.degree_level == "Masters"

    def test_assessment_result_model(self):
        result = AssessmentResult(
            overall_status=EligibilityStatus.LIKELY_ELIGIBLE,
            confidence=ConfidenceLevel.HIGH,
            student_summary=StudentSummary(
                nationality="India",
                highest_qualification="B.Tech CS",
                academic_score="78%",
            ),
            target=TargetInfo(
                university="Test Uni",
                country="UK",
                course="MSc AI",
                degree_level="Masters",
            ),
            assessment=[],
            document_consistency=DocumentConsistency(status=CategoryStatus.PASS),
            recommendation="Eligible to apply",
        )
        
        assert result.overall_status == EligibilityStatus.LIKELY_ELIGIBLE
        assert result.confidence == ConfidenceLevel.HIGH

    def test_eligibility_status_enum(self):
        assert EligibilityStatus.ELIGIBLE.value == "ELIGIBLE"
        assert EligibilityStatus.LIKELY_ELIGIBLE.value == "LIKELY ELIGIBLE"
        assert EligibilityStatus.POTENTIALLY_ELIGIBLE.value == "POTENTIALLY ELIGIBLE \u2014 REQUIRES VERIFICATION"
        assert EligibilityStatus.NOT_ELIGIBLE.value == "NOT ELIGIBLE"
        assert EligibilityStatus.INSUFFICIENT_INFORMATION.value == "INSUFFICIENT INFORMATION"

    def test_category_status_enum(self):
        assert CategoryStatus.PASS.value == "PASS"
        assert CategoryStatus.FAIL.value == "FAIL"
        assert CategoryStatus.REQUIRES_VERIFICATION.value == "REQUIRES VERIFICATION"
        assert CategoryStatus.NOT_APPLICABLE.value == "NOT APPLICABLE"

    def test_confidence_level_enum(self):
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.LOW.value == "LOW"