//
//  BenefitModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct BenefitModel : Codable {
    struct ConfirmationSubject : Codable {
        let subject: String
        let score: Int
    }
    
    let minClass: Int?
    let minDiplomaLevel: Int?
    let isBVI: Bool
    let confirmationSubjects: [ConfirmationSubject]?
    let fullScoreSubjects: [String]?
    var admissionRule: AdmissionRule? = nil
    var sourceRelation: String? = nil
    
    enum CodingKeys : String, CodingKey {
        case minClass = "min_class"
        case minDiplomaLevel = "min_diploma_level"
        case isBVI = "is_bvi"
        case confirmationSubjects = "confirmation_subjects"
        case fullScoreSubjects = "full_score_subjects"
        case admissionRule = "admission_rule"
        case sourceRelation = "source_relation"
    }
}


struct AdmissionRule: Codable {
    let admissionYear: Int
    let benefitTypes: [String]
    let values: [String: String]
    let conditions: [String]
    let sourceURL: String
    let location: [String: Int]?

    enum CodingKeys: String, CodingKey {
        case admissionYear = "admission_year"
        case benefitTypes = "benefit_types"
        case sourceURL = "source_url"
        case values, conditions, location
    }

    var benefitTitle: String {
        let names = ["bvi": "БВИ", "100_points": "100 баллов", "full_score": "100 баллов"]
        let types = benefitTypes.map { names[$0] ?? "Другая льгота" }
        return types.isEmpty ? "Условия" : types.joined(separator: " / ")
    }

    var summary: String { benefitTitle }

    var details: String {
        let titles = [
            "benefit": "Льгота", "program_scope": "Область действия",
            "grades": "Классы", "diplomas": "Дипломы",
            "confirmation_subjects": "Предметы подтверждения", "confirmation_score": "Баллы подтверждения",
            "full_score_subjects": "Предметы для 100 баллов", "olympiad_year": "Год олимпиады",
            "olympiad_name": "Олимпиада", "olympiad_profile": "Профиль",
            "olympiad_level": "Уровень", "olympiad_subject": "Предмет олимпиады",
            "winner": "Победитель", "prize_winner": "Призёр", "field_codes": "Коды направлений",
            "registry_number": "Номер в перечне", "document_number": "Номер строки"
        ]
        let preferred = ["benefit", "program_scope", "grades", "diplomas", "confirmation_subjects", "confirmation_score"]
        let keys = preferred.filter { values[$0] != nil } + values.keys.filter { !preferred.contains($0) }.sorted()
        let rows = keys.compactMap { key -> String? in
            guard let value = values[key], !value.isEmpty else { return nil }
            return "\(titles[key] ?? key): \(value)"
        }
        return (rows + conditions).joined(separator: "\n\n")
    }
}
