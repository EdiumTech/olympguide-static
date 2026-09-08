//
//  AuthManager.swift
//  olympguide
//
//  Created by Tom Tim on 18.02.2025.
//

import UIKit
import Combine
import GoogleSignIn

class AuthManager : AuthManagerProtocol {
    typealias Constants = AllConstants.AuthManager
    
    static let shared = AuthManager()
    
    lazy var networkService: NetworkServiceProtocol = NetworkService.shared
    
    var userEmail: String?
    
    @Published var isAuthenticated: Bool = false
    
    var isAuthenticatedPublisher: AnyPublisher<Bool, Never> {
            $isAuthenticated.eraseToAnyPublisher()
    }
    
    private var cancellables = Set<AnyCancellable>()
    
    private init() {}
    
    func login(
        email: String,
        password: String,
        completion: @escaping (Result<BaseServerResponse, NetworkError>) -> Void
    ) {
        let body: [String: Any] = [
            "email": email,
            "password": password
        ]
        
        networkService.request(
            endpoint: Constants.loginEndpoint,
            method: .post,
            queryItems: nil,
            body: body,
            shouldCache: false){ [weak self] (result: Result<BaseServerResponse, NetworkError>) in
                switch result {
                case .success(let response):
                    self?.isAuthenticated = true
                    completion(.success(response))
                case .failure(let error):
                    completion(.failure(error))
                }
            }
    }
    
    func checkSession() {
        networkService.request(
            endpoint: Constants.checkEndpoint,
            method: .get,
            queryItems: nil,
            body: nil,
            shouldCache: false
        ) { [weak self] (result: Result<BaseServerResponse, NetworkError>) in
            switch result {
            case .success:
                self?.isAuthenticated = true
            case .failure:
                self?.isAuthenticated = false
            }
        }
    }
    
    func logout(completion: ((Result<BaseServerResponse, NetworkError>) -> Void)? = nil) {
        networkService.request(
            endpoint: Constants.logoutEndpoint,
            method: .post,
            queryItems: nil,
            body: nil,
            shouldCache: false
        ) { [weak self] (result: Result<BaseServerResponse, NetworkError>) in
            switch result {
            case .success(let response):
                self?.isAuthenticated = false
                completion?(.success(response))
            case .failure(let error):
                completion?(.failure(error))
            }
        }
    }
    
    func googleSignIn(
        view: UIViewController,
        completion: @escaping (Result<String, NetworkError>) -> Void
    ) {
        guard let clientID = Bundle.main.object(forInfoDictionaryKey: "CLIENT_ID") as? String else { return }
        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config
        
        GIDSignIn.sharedInstance.signIn(withPresenting: view) { [weak self] signInResult, error in
            guard let self = self else { return }
            if let error = error {
                print("Ошибка авторизации: \(error.localizedDescription)")
                return
            }
            guard let signInResult = signInResult else {
                print("Не удалось получить результат авторизации")
                return
            }
            
            let user = signInResult.user
            guard let idToken = user.idToken?.tokenString else {
                print("Не удалось получить токен")
                return
            }
            userEmail = user.profile?.email
            self.sendTokenToBackend(with: idToken, completion: completion)
        }
    }
    
    func sendTokenToBackend(
        with idToken: String,
        completion: @escaping (Result<String, NetworkError>) -> Void
    ) {
        let body: [String: String] = [
            "token": idToken
        ]

        
        networkService.request(
            endpoint: Constants.googleEndpoint,
            method: .post,
            queryItems: nil,
            body: body,
            shouldCache: false
        ) { [weak self] (result: Result<BaseServerResponse, NetworkError>) in
            switch result {
            case .success(let response):
                guard let token = response.token else {
                    self?.isAuthenticated = true
                    return
                }
                completion(.success(token))
                self?.isAuthenticated = true
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
    
    func deleteAccount(completion: @escaping ((Result<BaseServerResponse, NetworkError>) -> Void)) {
        networkService.request(
            endpoint: Constants.deleteAccountEndpoint,
            method: .delete,
            queryItems: nil,
            body: nil,
            shouldCache: false
        ) { [weak self] (result: Result<BaseServerResponse, NetworkError>) in
            switch result {
            case .success(let response):
                self?.isAuthenticated = false
                completion(.success(response))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
    
    func appleSignIn(
        token: String,
        completion: @escaping ((Result<BaseServerResponse, NetworkError>) -> Void)
    ) {
        let body: [String: String] = [
            "token": token
        ]
        networkService.request(
            endpoint: Constants.appleEndpoint,
            method: .post,
            queryItems: nil,
            body: body,
            shouldCache: false
        ) { [weak self] (result: Result<BaseServerResponse, NetworkError>) in
            switch result {
            case .success:
                self?.isAuthenticated = true
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}
