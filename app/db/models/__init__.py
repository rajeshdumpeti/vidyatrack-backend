from app.db.models.school import School  # noqa: F401
from app.db.models.teacher import Teacher  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.otp_request import OtpRequest  # noqa: F401
from app.db.models.student import Student  # noqa: F401
from app.db.models.class_ import Class  # noqa: F401
from app.db.models.section import Section  # noqa: F401
from app.db.models.attendance_record import AttendanceRecord  # noqa: F401
from app.db.models.attendance_submission import AttendanceSubmission  # noqa: F401
from app.db.models.notification_outbox import NotificationOutbox  # noqa: F401
from app.db.models.subject import Subject  # noqa: F401
from app.db.models.marks_record import MarksRecord  # noqa: F401
from app.db.models.marks_submission import MarksSubmission  # noqa: F401
from app.db.models.notification_outbox import NotificationOutbox  # noqa: F401
from app.db.models.teacher_primary_section import TeacherPrimarySection
from app.db.models.section_subject_teacher import SectionSubjectTeacher
from app.db.models.user_school import UserSchool
from app.db.models.teacher_section_assignment import TeacherSectionAssignment
from app.db.models.homework_broadcast import HomeworkBroadcast
from app.db.models.parent_message import ParentMessage
from app.db.models.parent_message_recipient import ParentMessageRecipient
from app.db.models.school_contact import SchoolContact
from app.db.models.school_academic_details import SchoolAcademicDetails
from app.db.models.school_features import SchoolFeatures
from app.db.models.management_admin import ManagementAdmin
from app.db.models.school_onboarding_draft import SchoolOnboardingDraft
from app.db.models.idempotency_key import IdempotencyKey
from app.db.models.student_import_batch import StudentImportBatch
from app.db.models.principal_assignment_history import PrincipalAssignmentHistory
from app.db.models.principal_onboarding_session import PrincipalOnboardingSession
