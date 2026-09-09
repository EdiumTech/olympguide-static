import Foundation

struct EligibilityCheck: Decodable { let condition: String; let state: String; let detail: String }
struct DiplomaAssessment: Decodable {
    let status: String; let benefit: String; let reason: String; let checks: [EligibilityCheck]
    let diploma_id: Int; let source_rule: AdmissionRule
}
struct RecommendedProgram: Decodable {
    let program_id: Int; let name: String; let university: String; let status: String
    let assessments: [DiplomaAssessment]
}
struct RecommendationsResponse: Decodable { let total: Int; let items: [RecommendedProgram]; let message: String }
