//
//  OlympiadsWorker.swift
//  olympguide
//
//  Created by Tom Tim on 09.01.2025.
//

import Foundation

protocol OlympiadsWorkerLogic {
    func fetchOlympiads(
        with params: [Param],
        completion: @escaping (Result<[OlympiadModel], Error>) -> Void
    )
}

final class OlympiadsWorker : OlympiadsWorkerLogic {
    
    @InjectSingleton
    var networkService: NetworkServiceProtocol

    func fetchOlympiads(
        with params: [Param],
        completion: @escaping (Result<[OlympiadModel], Error>) -> Void
    ) {
        var queryItems: [URLQueryItem] = []

        for param in params {
            queryItems.append(param.urlValue)
        }
        
        networkService.request(
            endpoint: "/olympiads",
            method: .get,
            queryItems: queryItems,
            body: nil,
            shouldCache: false
        ) { (result: Result<[OlympiadModel]?, NetworkError>) in
            switch result {
            case .success(let olympiads):
                let rows = olympiads ?? []
                guard rows.allSatisfy({ $0.academicYear == "2026/2027" && (1...3).contains($0.level) && !$0.profile.isEmpty }) else {
                    completion(.failure(NSError(domain: "OlympGuide", code: 409, userInfo: [NSLocalizedDescriptionKey: "Каталог РСОШ 2026/2027 ещё не обновлён на сервере. Попробуйте позже."])))
                    return
                }
                completion(.success(rows))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}
