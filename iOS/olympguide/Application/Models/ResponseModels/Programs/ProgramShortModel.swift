import Foundation

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
    let budgetPlaces: Int?
    let paidPlaces: Int?
    let cost: Int?
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
    
    var quantities: ProgramQuantities {
        ProgramQuantities(
            budgetPlaces: admissionMetadata?.placesKnown == false ? nil : budgetPlaces,
            paidPlaces: admissionMetadata?.placesKnown == false ? nil : paidPlaces,
            cost: admissionMetadata?.costKnown == false ? nil : cost,
            metadata: admissionMetadata
        )
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
            costKnown: admissionMetadata?.costKnown ?? true,
            admissionMetadata: admissionMetadata
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
    var costPeriod: String? = nil
    var placesNote: String? = nil
    var quantityNotes: [String]? = nil
    var studyForm: String? = nil
    var admissionYear: Int? = nil
    var quantityEvidence: [String: ProgramQuantityEvidence]? = nil
    enum CodingKeys: String, CodingKey {
        case placesKnown = "places_known"
        case costKnown = "cost_known"
        case costPeriod = "cost_period"
        case placesNote = "places_note"
        case quantityNotes = "quantity_notes"
        case studyForm = "study_form"
        case admissionYear = "admission_year"
        case quantityEvidence = "quantity_evidence"
    }
}

struct ProgramQuantityEvidence: Codable {
    let sourceURL: String?
    let locator: String?
    enum CodingKeys: String, CodingKey {
        case sourceURL = "source_url"
        case locator
    }
}

/// Shared presentation for both program list cells and the initial/detail refresh.
/// Nil means unknown; an explicitly recorded zero remains visible as zero.
struct ProgramQuantities {
    let budgetPlaces: Int?
    let paidPlaces: Int?
    let cost: Int?
    var metadata: ProgramAdmissionMetadata? = nil

    static let unknown = ProgramQuantities(budgetPlaces: nil, paidPlaces: nil, cost: nil)
    private var sharedMarker: String { metadata?.placesNote == nil ? "" : "*" }
    var budgetText: String { budgetPlaces.map { String($0) + sharedMarker } ?? "Нет данных" }
    var paidText: String { paidPlaces.map { String($0) + sharedMarker } ?? "Нет данных" }
    var summaryText: String {
        var parts: [String] = []
        if let year = metadata?.admissionYear { parts.append("Приём \(year)") }
        if let form = metadata?.studyForm { parts.append(form) }
        if metadata?.placesNote != nil { parts.append("* Общий набор") }
        return parts.joined(separator: " · ")
    }
    var detailText: String {
        ([summaryText, metadata?.placesNote ?? ""] + (metadata?.quantityNotes ?? []))
            .filter { !$0.isEmpty }.joined(separator: "\n\n")
    }
    var costText: String {
        guard let cost = cost else { return paidPlaces == 0 ? "Нет платного набора" : "Нет данных" }
        let formatter = NumberFormatter()
        formatter.locale = Locale(identifier: "ru_RU")
        formatter.numberStyle = .decimal
        formatter.groupingSeparator = " "
        let period = metadata?.costPeriod == "semester" ? "семестр" : "год"
        return "\(formatter.string(from: NSNumber(value: cost)) ?? String(cost)) ₽/\(period)"
    }
}
