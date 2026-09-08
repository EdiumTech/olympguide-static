import Foundation

struct PersonalExam: Codable { let subject: String; let score: Int; let year: Int }
struct PersonalApplicant: Codable { let admission_year: Int?; let exams: [PersonalExam] }
