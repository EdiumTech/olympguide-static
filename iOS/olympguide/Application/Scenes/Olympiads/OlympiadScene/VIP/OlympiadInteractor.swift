//
//  Interactor.swift
//  olympguide
//
//  Created by Tom Tim on 04.03.2025.
//

import Foundation
import Combine

final class OlympiadInteractor : OlympiadDataStore {
    @InjectSingleton
    var favoritesManager: FavoritesManagerProtocol
    
    private var cancellables = Set<AnyCancellable>()
    
    var presenter: (OlympiadPresentationLogic & BenefitsByProgramsPresentationLogic)?
    var worker: (OlympiadWorkerLogic & BenefitsByProgramsWorkerLogic)?
    var universities: [UniversityModel]?
    var allUniversities: [UniversityModel]?
    var programs: [[ProgramWithBenefitsModel]]?
    private var catalogueVersion = UUID()
    var olympiadId: Int?
    var isFavorite: Bool?
    
    init() {
        setupOlympiadBindings()
    }
}

extension OlympiadInteractor : OlympiadBusinessLogic {
    func loadUniversities(with request: Olympiad.LoadUniversities.Request) {
        catalogueVersion = UUID()
        let version = catalogueVersion
        self.olympiadId = request.olympiadID
        worker?.fetchUniversities(
            for: request.olympiadID
        ) { [weak self] result in
            guard let self, self.catalogueVersion == version else { return }
            switch result {
            case .success(let universities):
                self.universities = universities
                if self.allUniversities == nil {
                    self.allUniversities = universities
                }
                self.programs = [[ProgramWithBenefitsModel]] (repeating: [], count: universities.count)
                let response = Olympiad.LoadUniversities.Response(universities: universities)
                self.presenter?.presentLoadUniversities(with: response)
            case .failure(let error):
                let response = Olympiad.LoadUniversities.Response(error: error)
                self.presenter?.presentLoadUniversities(with: response)
            }
        }
    }
    
    func favoriteStatusAt(index: Int) -> Bool {
        return universities?[index].like ?? false
    }
    
    func setFavoriteStatus(_ status: Bool, to universityId: Int) {
        if let index = universities?.firstIndex(where: { $0.universityID == universityId }) {
            universities?[index].like = status
        }
    }
    
    func universityModel(at index: Int) -> UniversityModel? {
        universities?[index]
    }
}

extension OlympiadInteractor : BenefitsByProgramsBusinessLogic {
    func loadBenefits(with request: BenefitsByPrograms.Load.Request) {
        let version = catalogueVersion
        let params: [Param] = request.params.flatMap { key, value in
            value.array
        }
        worker?.fetchBenefits(
            for: request.olympiadID,
            and: request.universityID,
            with: params
        ) { [weak self] result in
            guard let self, self.catalogueVersion == version,
                  let universities = self.universities, universities.indices.contains(request.section),
                  universities[request.section].universityID == request.universityID,
                  self.programs?.indices.contains(request.section) == true else { return }
            switch result {
            case .success(let programs):
                self.programs?[request.section] = programs ?? []
                let response = BenefitsByPrograms.Load.Response(programs: programs ?? [], section: request.section)
                self.presenter?.presentLoadBenefits(with: response)
            case .failure(let error):
                let response = BenefitsByPrograms.Load.Response(error: error)
                self.presenter?.presentLoadBenefits(with: response)
            }
        }
    }
}

extension OlympiadInteractor {
    private func setupOlympiadBindings() {
        favoritesManager.olympiadEventSubject
            .receive(on: DispatchQueue.main)
            .sink { [weak self] event in
                guard let self = self else { return }
                guard olympiadId == event.id else { return }
                switch event {
                case .added:
                    presenter?.presentSetFavorite(to: true)
                case .removed:
                    presenter?.presentSetFavorite(to: false)
                case .error:
                    guard let isFavorite = isFavorite else { return }
                    presenter?.presentSetFavorite(to: isFavorite)
                case .access(_, let isFavorite):
                    self.isFavorite = isFavorite
                }
            }
            .store(in: &cancellables)
    }
}

