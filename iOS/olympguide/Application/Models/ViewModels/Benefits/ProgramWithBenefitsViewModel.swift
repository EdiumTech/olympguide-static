//
//  ProgramWithBenefitsViewModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

class ProgramWithBenefitsViewModel {
    struct Program {
        let programID: Int
        let programName: String
        let field: String
        let university: String
    }
    
    struct BenefitInformationViewModel {
        let minClass: Int?
        let minDiplomaLevel: Int?
        let isBVI: Bool
        
        let confirmationSubjects: [BenefitModel.ConfirmationSubject]?
        let fullScoreSubjects: [String]?
        var admissionRule: AdmissionRule? = nil
        var sourceRelation: String? = nil
    }
    
    let program: Program
    let benefitInformation: [BenefitInformationViewModel]
    
    init(program: Program, benefitInformation: [BenefitInformationViewModel]) {
        self.program = program
        self.benefitInformation = benefitInformation
    }
}
