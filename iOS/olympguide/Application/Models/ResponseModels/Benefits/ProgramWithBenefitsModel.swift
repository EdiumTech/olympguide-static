//
//  ProgramWithBenefitsModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct ProgramWithBenefitsModel : Codable {
    struct Program: Codable {
        let programID: Int
        let name: String
        let field: String
        let university: String
        let universityID: Int
        
        enum CodingKeys: String, CodingKey {
            case programID = "program_id"
            case universityID = "university_id"
            case name, field, university
        }
    }
    
    let program: Program
    let benefits: [BenefitModel]
    
    func toViewModel() -> ProgramWithBenefitsViewModel {
        ProgramWithBenefitsViewModel(
            program: ProgramWithBenefitsViewModel.Program(
                programID: program.programID,
                programName: program.name,
                field: program.field,
                university: program.university
            ),
            benefitInformation: benefits.map {
                ProgramWithBenefitsViewModel.BenefitInformationViewModel(
                    minClass: $0.minClass,
                    minDiplomaLevel: $0.minDiplomaLevel,
                    isBVI: $0.isBVI,
                    confirmationSubjects: $0.confirmationSubjects,
                    fullScoreSubjects: $0.fullScoreSubjects,
                    admissionRule: $0.admissionRule,
                    sourceRelation: $0.sourceRelation
                )
            }
        )
    }
}
