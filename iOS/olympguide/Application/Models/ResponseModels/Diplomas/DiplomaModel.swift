//
//  DiplomaModel.swift
//  olympguide
//
//  Created by Tom Tim on 23.03.2025.
//

struct DiplomaModel : Codable {
    let id: Int
    let diplomaClass: Int
    let level: Int
    var olympiadID: Int? = nil
    var awardYear: Int? = nil
    var olympiadYear: String? = nil
    var profile: String? = nil
    var result: String? = nil
    
    let olympiad: OlympiadShortModel
    
    enum CodingKeys : String, CodingKey {
        case id = "diploma_id"
        case diplomaClass = "class"
        case level, olympiad
        case olympiadID = "olympiad_id"
        case awardYear = "award_year"
        case olympiadYear = "olympiad_year"
        case profile, result
    }
    
    func toViewModel() -> DiplomaViewModel {
        return DiplomaViewModel(
            diplomaClass: diplomaClass,
            level: level,
            olympiadName: olympiad.name,
            olympiadLevel: olympiad.level,
            olympiadProfile: olympiad.profile
        )
    }
}
