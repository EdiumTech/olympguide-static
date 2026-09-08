//
//  OlympiadWithBenefitsModel.swift
//  olympguide
//
//  Created by Tom Tim on 06.03.2025.
//

struct OlympiadWithBenefitsModel : Codable {
    struct Olympiad : Codable {
        let olympiadID: Int
        let name: String
        let level: Int
        let profile: String
        
        enum CodingKeys: String, CodingKey {
            case olympiadID = "olympiad_id"
            case name, profile, level
        }
    }
    
    let olympiad: Olympiad
    let benefits: [BenefitModel]
    
    func toViewModel() -> [OlympiadWithBenefitViewModel] {
        benefits.map { benefit in
            OlympiadWithBenefitViewModel(
                olympiadName: olympiad.name,
                olympiadLevel: olympiad.level,
                olympiadProfile: olympiad.profile,
                minClass: benefit.minClass,
                minDiplomaLevel: benefit.minDiplomaLevel,
                isBVI: benefit.isBVI,
                confirmationSubjects: benefit.confirmationSubjects,
                fullScoreSubjects: benefit.fullScoreSubjects,
                admissionRule: benefit.admissionRule,
                sourceRelation: benefit.sourceRelation
            )
        }
    }
}
