//
//  ProgramShortModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct ProgramShortModel : Codable {
    let programID: Int
    let name: String
    let field: String
    let budgetPlaces: Int
    let paidPlaces: Int
    let cost: Int
    let requiredSubjects: [String]
    let optionalSubjects: [String]?
    var like: Bool
    let link: String
    var admissionMetadata: ProgramAdmissionMetadata? = nil
    
    enum CodingKeys : String, CodingKey {
        case admissionMetadata = "admission_metadata"
        case programID = "program_id"
        case budgetPlaces = "budget_places"
        case paidPlaces = "paid_places"
        case name, field, cost, like, link
        case requiredSubjects = "required_subjects"
        case optionalSubjects = "optional_subjects"
    }
    
    func toViewModel() -> ProgramViewModel {
        ProgramViewModel(
            programID: programID,
            name: name,
            code: field,
            budgetPlaces: budgetPlaces,
            paidPlaces: paidPlaces,
            cost: cost,
            like: like,
            requiredSubjects: requiredSubjects,
            optionalSubjects: optionalSubjects,
            placesKnown: admissionMetadata?.placesKnown ?? true,
            costKnown: admissionMetadata?.costKnown ?? true
        )
    }
}

extension ProgramShortModel : Equatable {
    static func == (lhs: ProgramShortModel, rhs: ProgramShortModel) -> Bool {
        lhs.programID == rhs.programID
    }

    static func == (lhs: ProgramShortModel, rhs: ProgramViewModel) -> Bool {
        lhs.programID == rhs.programID
    }
}


struct ProgramAdmissionMetadata: Codable {
    let placesKnown: Bool
    let costKnown: Bool
    enum CodingKeys: String, CodingKey {
        case placesKnown = "places_known"
        case costKnown = "cost_known"
    }
}
