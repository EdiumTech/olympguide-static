//
//  OlympiadWithBenefitViewModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct OlympiadWithBenefitViewModel {
    let olympiadName: String
    let olympiadLevel: Int
    let olympiadProfile: String
    let minClass: Int?
    let minDiplomaLevel: Int?
    let isBVI: Bool
    
    let confirmationSubjects: [BenefitModel.ConfirmationSubject]?
    let fullScoreSubjects: [String]?
    var admissionRule: AdmissionRule? = nil
    var sourceRelation: String? = nil
}
