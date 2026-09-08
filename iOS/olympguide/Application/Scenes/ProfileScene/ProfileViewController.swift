//
//  ProfileViewController.swift
//  olympguide
//
//  Created by Tom Tim on 10.01.2025.
//

import UIKit
import Combine
import AuthenticationServices

// MARK: - Constants
fileprivate enum Constants {
    enum Colors {
        static let refreshTint = UIColor.systemCyan
        static let searchButtonTint = UIColor.black
        static let tableViewBackground = UIColor.white
        static let titleLabelTextColor = UIColor.black
    }
    
    enum Fonts {
        static let titleLabelFont = FontManager.shared.font(for: .largeTitleLabel)
    }
    
    enum Dimensions {
        static let titleLabelTopMargin: CGFloat = 25
        static let titleLabelLeftMargin: CGFloat = 20
        static let searchButtonSize: CGFloat = 33
        static let searchButtonRightMargin: CGFloat = 20
        static let tableViewTopMargin: CGFloat = 13
    }
    
    enum Strings {
        static let profileTitle = "Профиль"
        static let backButtonTitle = "Профиль"
    }
    
    enum Images {
        static let searchIcon: String =  "magnifyingglass"
    }
}

class ProfileViewController: UIViewController {
    @InjectSingleton
    var authManager: AuthManagerProtocol
    var interactor: ProfileBusinessLogic?
    var router: ProfileRoutingLogic?
    let authLabels: [String] = [
        "Личные данные",
        "Мои дипломы",
        "Избранные ВУЗы",
        "Избранные программы",
        "Избранные олимпиады",
        //        "Тема приложения",
        "О нас"
    ]
    
    let nonAuthLabels: [String] = [
        "О нас"
    ]
    
    private let tableView = UITableView(frame: .zero, style: .plain)
    private var cancellables = Set<AnyCancellable>()
    private var didSetInitialContentOffset = false
    
    override func viewDidLoad() {
        super.viewDidLoad()

        extendedLayoutIncludesOpaqueBars = true
        
        configureNavigationBar()
        configureTableView()
        
        let backItem = UIBarButtonItem(
            title: Constants.Strings.backButtonTitle,
            style: .plain,
            target: nil,
            action: nil
        )
        
        navigationItem.backBarButtonItem = backItem
        
        authManager.isAuthenticatedPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self]  _ in
                self?.tableView.reloadData()
            }.store(in: &cancellables)
        
    }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)

        guard !didSetInitialContentOffset else { return }
        didSetInitialContentOffset = true
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            tableView.layoutIfNeeded()
            tableView.setContentOffset(
                CGPoint(x: 0, y: -tableView.adjustedContentInset.top),
                animated: false
            )
        }
    }
    
    private func configureNavigationBar() {
        navigationItem.title = Constants.Strings.profileTitle
        if #available(iOS 26.0, *) {
            navigationItem.largeTitle = Constants.Strings.profileTitle
            navigationItem.largeTitleDisplayMode = .inline
        } else {
            navigationItem.largeTitleDisplayMode = .always
        }
    }
    
    private func configureTableView() {
        view.addSubview(tableView)
        
        tableView.separatorStyle = .none
        tableView.frame = view.bounds
        
        tableView.backgroundColor = .white
        
        tableView.contentInset = UIEdgeInsets(top: 0, left: 0, bottom: 50, right: 0)
        
        tableView.dataSource = self
        tableView.delegate = self
        
        let footerView = UIView(frame: CGRect(x: 0, y: 0, width: view.frame.width, height: 40))
        
        let versionLabel = UILabel(frame: footerView.bounds)
        versionLabel.textAlignment = .center
        versionLabel.font = FontManager.shared.font(for: .additionalInformation)
        versionLabel.textColor = .gray
        
        if
            let version = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String,
            let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String
        {
            versionLabel.text = "Версия приложения \(version) (\(build))"
        }
        
        footerView.addSubview(versionLabel)
        tableView.tableFooterView = footerView
    }
    
    // MARK: - Actions
    @objc private func registerButtonTapped() {
        router?.routeToSignUp()
    }
    
    @objc private func loginButtonTapped() {
        router?.routeToSignIn()
    }
    
    @objc private func logoutButtonTapped() {
        authManager.logout { [weak self] result in
            if case .failure(let error) = result {
                self?.showAlert(with: error.localizedDescription)
            }
        }
    }
    
    @objc private func deleteButtonTapped() {
        let alert = UIAlertController(title: "Вы уверены?", message: "Все данные будут удалены без возможности восстановления", preferredStyle: .alert)
        
        alert.addAction(UIAlertAction(title: "Отмена", style: .cancel, handler: nil))
        alert.addAction(UIAlertAction(title: "Да", style: .default, handler: { _ in
            self.authManager.deleteAccount { [weak self] result in
                if case .failure(let error) = result {
                    self?.showAlert(with: error.localizedDescription)
                }
            }
        }))
        
        present(alert, animated: true, completion: nil)
    }
}

import GoogleSignIn

// MARK: - UITableViewDataSource
extension ProfileViewController: UITableViewDataSource {
    func numberOfSections(in tableView: UITableView) -> Int {
        return 1
    }
    
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        if authManager.isAuthenticated {
            return authLabels.count + 2
        } else {
            return nonAuthLabels.count + 4
        }
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        if !authManager.isAuthenticated {
            if indexPath.row == 0 {
                let cell = ProfileButtonTableViewCell()
                cell.configure(
                    title: "Зарегистрироваться",
                    borderColor: UIColor(hex: "#FF2D55"),
                    textColor: .black
                )
                cell.actionButton.addTarget(
                    self,
                    action: #selector(registerButtonTapped),
                    for: .touchUpInside
                )
                return cell
            } else if indexPath.row == 1 {
                let cell = ProfileButtonTableViewCell()
                cell.configure(
                    title: "Войти",
                    borderColor: UIColor(hex: "#32ADE6"),
                    textColor: .black
                )
                cell.actionButton.addTarget(
                    self,
                    action: #selector(loginButtonTapped),
                    for: .touchUpInside
                )
                return cell
            } else if indexPath.row == 2 {
                let cell = GoogleSignInButtonTableViewCell()
                cell.actionButton.addTarget(
                    self,
                    action: #selector(googleSignInButtonTapped),
                    for: .touchUpInside
                )
                
                return cell
            } else if indexPath.row == 3 {
                let cell = AppleSignInButtonTableViewCell()
                cell.actionButton.addTarget(
                    self,
                    action: #selector(appleSignINButtonTapped),
                    for: .touchUpInside
                )
                
                return cell
            } else {
                let cell = ProfileTableViewCell()
                cell.configure(title: nonAuthLabels[indexPath.row - 4])
                cell.hideSeparator(indexPath.row == nonAuthLabels.count + 4 - 1)
                return cell
            }
        } else {
            if indexPath.row <= authLabels.count - 1 {
                let cell = ProfileTableViewCell()
                cell.configure(title: authLabels[indexPath.row])
                cell.hideSeparator(indexPath.row == authLabels.count - 1)
                return cell
            } else if indexPath.row == authLabels.count {
                let cell = ProfileButtonTableViewCell()
                cell.configure(
                    title: "Выйти",
                    borderColor: UIColor(hex: "#FF2D55"),
                    textColor: .black
                )
                cell.actionButton.addTarget(
                    self,
                    action: #selector(logoutButtonTapped),
                    for: .touchUpInside
                )
                return cell
            } else {
                let cell = ProfileButtonTableViewCell()
                cell.configure(
                    title: "Удалить аккаунт",
                    borderColor: UIColor(hex: "#FF2D55"),
                    textColor: .black
                )
                cell.actionButton.addTarget(
                    self,
                    action: #selector(deleteButtonTapped),
                    for: .touchUpInside
                )
                return cell
            }
        }
    }
    
    @objc func googleSignInButtonTapped() {
        authManager.googleSignIn(
            view: self
        ) { [weak self] result in
            switch result {
            case .success(_):
                return
            case .failure(let error):
                self?.showAlert(with: error.localizedDescription)
            }
        }
    }
    
    @objc func appleSignINButtonTapped() {
        let request = ASAuthorizationAppleIDProvider().createRequest()
        request.requestedScopes = [.fullName, .email]
        
        let controller = ASAuthorizationController(authorizationRequests: [request])
        controller.delegate = self
        controller.presentationContextProvider = self
        controller.performRequests()
    }
}

extension ProfileViewController: ASAuthorizationControllerDelegate, ASAuthorizationControllerPresentationContextProviding {
    
    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        return self.view.window!
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithAuthorization authorization: ASAuthorization) {
        if let credential = authorization.credential as? ASAuthorizationAppleIDCredential {
            let identityToken = credential.identityToken
            let tokenString = String(data: identityToken ?? Data(), encoding: .utf8)
            guard let tokenString = tokenString else { return }
            
            authManager.appleSignIn(token: tokenString) { [weak self] result in
                switch result {
                case .success:
                    return
                case .failure:
                    self?.showAlert(with: "Не удалось завершить авторизацию")
                }
            }
        }
    }

    func authorizationController(controller: ASAuthorizationController, didCompleteWithError error: Error) {
//        showAlert(with: "Не удалось завершить авторизацию")
    }
}

// MARK: - UITableViewDelegate
extension ProfileViewController : UITableViewDelegate {
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        guard
            let cell = tableView.cellForRow(at: indexPath) as? ProfileTableViewCell
        else { return }
        
        switch cell.label.text {
        case "О нас":
            router?.routToAboutUs()
        case "Избранные олимпиады":
            router?.routToFavoriteOlympiads()
        case "Избранные ВУЗы":
            router?.routToFavoriteUniversities()
        case "Избранные программы":
            router?.routToFavoritePrograms()
        case "Мои дипломы":
            router?.routeToDiplomas()
        case "Личные данные":
            interactor?.loadUser(with: Profile.User.Request())
        default:
            break
        }
        
    }
}

extension ProfileViewController: ProfileDisplayLogic {
    func displayLoadUser(with viewModel: Profile.User.ViewModel) {
        router?.routeToPersonalData()
    }
}
