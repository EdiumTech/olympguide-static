//
//  ProgramViewModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

class ProgramViewModel {
    let programID: Int
    let name: String
    let code: String
    let budgetPlaces: Int
    let paidPlaces: Int
    let cost: Int
    let placesKnown: Bool
    let costKnown: Bool
    var like: Bool
    let requiredSubjects: [String]
    let optionalSubjects: [String]?
    
    init(
        programID: Int,
        name: String,
        code: String,
        budgetPlaces: Int,
        paidPlaces: Int,
        cost: Int,
        like: Bool,
        requiredSubjects: [String],
        optionalSubjects: [String]?,
        placesKnown: Bool = true,
        costKnown: Bool = true
    ) {
        self.programID = programID
        self.name = name
        self.code = code
        self.budgetPlaces = budgetPlaces
        self.paidPlaces = paidPlaces
        self.cost = cost
        self.placesKnown = placesKnown
        self.costKnown = costKnown
        self.like = like
        self.requiredSubjects = requiredSubjects
        self.optionalSubjects = optionalSubjects
    }
}
