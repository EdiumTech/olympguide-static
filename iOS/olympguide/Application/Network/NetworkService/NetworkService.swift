//
//  NetworkService.swift
//  olympguide
//
//  Created by Tom Tim on 26.01.2025.
//

import Foundation
import Combine

protocol NetworkServiceProtocol {
    func request<T: Decodable>(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?,
        shouldCache: Bool,
        completion: @escaping (Result<T, NetworkError>) -> Void
    )
    
    func requestWithBearer<T: Decodable>(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?,
        bearerToken: String,
        shouldCache: Bool,
        completion: @escaping (Result<T, NetworkError>) -> Void
    )
}

final class NetworkService: NetworkServiceProtocol {
    @InjectSingleton
    var authManager: AuthManagerProtocol
    
    private var cancellables = Set<AnyCancellable>()

    static let shared = NetworkService()
    
    private let cache = NSCache<NSString, NSData>()
    
    private init() {
        setupAuthBindings()
    }
    
    // MARK: - Подготовка запроса
    private func prepareRequest(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?
    ) -> URLRequest? {
        guard let url = APIConfiguration.url(for: endpoint, queryItems: queryItems) else { return nil }
        
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        // URLSession.shared handles the server's Secure/HttpOnly session cookie.
        request.httpShouldHandleCookies = true
        request.cachePolicy = .reloadIgnoringLocalCacheData
        
        if let body = body {
            do {
                request.httpBody = try JSONSerialization.data(withJSONObject: body, options: [])
            } catch {
                return nil
            }
        }
        return request
    }

    // MARK: - Логика кэширования
    private func cachedData(for request: URLRequest) -> Data? {
        guard let urlString = request.url?.absoluteString else { return nil }
        let cacheKey = urlString as NSString
        return cache.object(forKey: cacheKey) as Data?
    }

    private func cache(data: Data, for request: URLRequest) {
        guard let urlString = request.url?.absoluteString else { return }
        let cacheKey = urlString as NSString
        cache.setObject(data as NSData, forKey: cacheKey)
    }

    // MARK: - Обработка ответа
    private func processResponse<T: Decodable>(
        data: Data?,
        response: URLResponse?,
        error: Error?,
        for request: URLRequest,
        method: HTTPMethod,
        shouldCache: Bool,
        completion: @escaping (Result<T, NetworkError>) -> Void
    ) {
        DispatchQueue.main.async {
            if let error = error {
                completion(.failure(.unknown(message: error.localizedDescription)))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(.unknown(message: "No HTTP response")))
                return
            }
            
            let result: Result<T, NetworkError> = HTTPResponseDecoder.decode(
                data: data, statusCode: httpResponse.statusCode
            )
            if case .success = result, method == .get, shouldCache, let data = data {
                self.cache(data: data, for: request)
            }
            completion(result)
        }
    }

    // MARK: - Основной метод запроса
    func request<T: Decodable>(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?,
        shouldCache: Bool = true,
        completion: @escaping (Result<T, NetworkError>) -> Void
    ) {
        guard let request = prepareRequest(endpoint: endpoint, method: method, queryItems: queryItems, body: body) else {
            completion(.failure(.invalidURL))
            return
        }
        
        if method == .get && shouldCache, let cachedData = cachedData(for: request) {
            do {
                let decodedData = try JSONDecoder().decode(T.self, from: cachedData)
                completion(.success(decodedData))
            } catch {
                completion(.failure(.decodingError))
            }
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            self.processResponse(
                data: data,
                response: response,
                error: error,
                for: request,
                method: method,
                shouldCache: shouldCache,
                completion: completion
            )
        }
        .resume()
    }
    
    private func prepareRequestWithBearer(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?,
        bearerToken: String
    ) -> URLRequest? {
        guard var request = prepareRequest(
            endpoint: endpoint, method: method, queryItems: queryItems, body: body
        ) else { return nil }
        request.setValue("Bearer \(bearerToken)", forHTTPHeaderField: "Authorization")
        return request
    }

    func requestWithBearer<T: Decodable>(
        endpoint: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem]?,
        body: [String: Any]?,
        bearerToken: String,
        shouldCache: Bool = true,
        completion: @escaping (Result<T, NetworkError>) -> Void
    ) {
        guard let request = prepareRequestWithBearer(
            endpoint: endpoint,
            method: method,
            queryItems: queryItems,
            body: body,
            bearerToken: bearerToken
        ) else {
            completion(.failure(.invalidURL))
            return
        }
        
        if method == .get && shouldCache, let cachedData = cachedData(for: request) {
            do {
                let decodedData = try JSONDecoder().decode(T.self, from: cachedData)
                completion(.success(decodedData))
            } catch {
                completion(.failure(.decodingError))
            }
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            self.processResponse(
                data: data,
                response: response,
                error: error,
                for: request,
                method: method,
                shouldCache: shouldCache,
                completion: completion
            )
        }
        .resume()
    }
    
    private func setupAuthBindings() {
        authManager.isAuthenticatedPublisher
            .removeDuplicates()
            .sink { [weak self] _ in
                // Clear synchronously before observers request data for the next session.
                self?.cache.removeAllObjects()
            }.store(in: &cancellables)
    }
}
