//
//  OlympiadPresenter.swift
//  olympguide
//
//  Created by Tom Tim on 04.03.2025.
//

import UIKit

final class OlympiadPresenter : OlympiadPresentationLogic {
    weak var viewController: (OlympiadDisplayLogic & BenefitsByProgramsDisplayLogic & UIViewController)?
    
    func presentLoadUniversities(with response: Olympiad.LoadUniversities.Response) {
        if let error = response.error {
            viewController?.showAlert(with: error.localizedDescription)
            return
        }
        
        guard let universitites = response.universities else {
            return
        }
        
        let universitiesViewModel = universitites.map { $0.toViewModel() }
        
        let viewModel = Olympiad.LoadUniversities.ViewModel(universities: universitiesViewModel)
        viewController?.displayLoadUniversitiesResult(with: viewModel)
    }
    
    func presentSetFavorite(to isFavorite: Bool) {
        viewController?.displaySetFavorite(to: isFavorite)
    }
}

extension OlympiadPresenter : BenefitsByProgramsPresentationLogic {
    func presentLoadBenefits(with response: BenefitsByPrograms.Load.Response) {
        if let error = response.error {
            viewController?.showAlert(with: error.localizedDescription)
            return
        }
        
        guard
            let programs = response.programs,
            let section = response.section
        else {
            return
        }
        
        let programsViewModel = programs.map { model in
            let program = ProgramWithBenefitsViewModel.Program(
                programID: model.program.programID,
                programName: model.program.name,
                field: model.program.field,
                university: model.program.university
            )
            
            let benefitInformation = model.benefits.map { benefit in
                ProgramWithBenefitsViewModel.BenefitInformationViewModel(
                    minClass: benefit.minClass,
                    minDiplomaLevel: benefit.minDiplomaLevel,
                    isBVI: benefit.isBVI,
                    confirmationSubjects: benefit.confirmationSubjects,
                    fullScoreSubjects: benefit.fullScoreSubjects,
                    admissionRule: benefit.admissionRule,
                    sourceRelation: benefit.sourceRelation
                )
            }
            
            return ProgramWithBenefitsViewModel(
                program: program,
                benefitInformation: benefitInformation
            )
        }
        
        let viewModel = BenefitsByPrograms.Load.ViewModel(
            benefits: programsViewModel,
            section: section
        )
        viewController?.displayLoadBenefitsResult(with: viewModel)
    }
}
