//
//  ProgramModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct ProgramModel : Codable {
    let programID: Int
    let name: String
    let field: String
    let budgetPlaces: Int?
    let paidPlaces: Int?
    let cost: Int?
    let requiredSubjects: [String]
    let optionalSubjects: [String]
    var like: Bool
    let university: UniversityModel
    let link: String
    var admissionMetadata: ProgramAdmissionMetadata? = nil
    
    enum CodingKeys : String, CodingKey {
        case admissionMetadata = "admission_metadata"
        case programID = "program_id"
        case budgetPlaces = "budget_places"
        case paidPlaces = "paid_places"
        case requiredSubjects = "required_subjects"
        case optionalSubjects = "optional_subjects"
        case name, field, cost, like, link, university
    }
    
    func toShortModel() -> ProgramShortModel {
        ProgramShortModel(
            programID: programID,
            name: name,
            field: field,
            budgetPlaces: budgetPlaces,
            paidPlaces: paidPlaces,
            cost: cost,
            requiredSubjects: requiredSubjects,
            optionalSubjects: optionalSubjects,
            like: like,
            link: link,
            admissionMetadata: admissionMetadata
        )
    }
}
