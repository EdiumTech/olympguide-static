//
//  DiplomaPresenter.swift
//  olympguide
//
//  Created by Vladislav Pankratov on 26.04.2025.
//

import UIKit

final class DiplomaPresenter : DiplomaPresentationLogic {
    weak var viewController: (DiplomaDisplayLogic & BenefitsByProgramsDisplayLogic & UIViewController)?
    
    func presentLoadUniversities(with response: Diploma.LoadUniversities.Response) {
        if let error = response.error {
            viewController?.showAlert(with: error.localizedDescription)
            return
        }
        
        guard let universitites = response.universities else {
            return
        }
        
        let universitiesViewModel = universitites.map { $0.toViewModel() }
        
        let viewModel = Diploma.LoadUniversities.ViewModel(universities: universitiesViewModel)
        viewController?.displayLoadUniversitiesResult(with: viewModel)
    }
}

extension DiplomaPresenter : BenefitsByProgramsPresentationLogic {
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

