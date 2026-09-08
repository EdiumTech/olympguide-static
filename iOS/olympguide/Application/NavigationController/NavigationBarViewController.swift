//
//  NavigationBarViewController.swift
//  olympguide
//
//  Created by Tom Tim on 12.01.2025.
//

import UIKit
import Combine

protocol NonTabBarVC { }
protocol WithBookMarkButton { }

fileprivate enum Constants {
    enum Colors {
        static let searchButtonTintColor: UIColor = .black
    }
    
    enum Dimensions {
        static let searchButtonSize: CGFloat = 33
        static let bookMarkkButtonSize: CGFloat = 28
        static let searchButtonBottomMargin: CGFloat = 8
        static let searchButtonRightMargin: CGFloat = 20
        static let animateDuration: TimeInterval = 0.1
    }
    
    enum Images {
        static let searchIcon: String =  "magnifyingglass"
        static let bookmarkIcon: String = "bookmark"
    }
}

class NavigationBarViewController : UINavigationController {
    @InjectSingleton
    var authManager: AuthManagerProtocol
    
    var searchButtonPressed: ((_: UIButton) -> Void)?
    var bookMarkButtonPressed: ((_: UIButton) -> Void)?
    var plusButtonPressed: ((_: UIButton) -> Void)?
    private var cancellables = Set<AnyCancellable>()
    
    private let searchButton: UIButton = {
        let button = UIButton()
        button.setImage(UIImage(systemName: Constants.Images.searchIcon), for: .normal)
        button.tintColor = Constants.Colors.searchButtonTintColor
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.imageView?.contentMode = .scaleAspectFit
        return button
    }()
    
    let bookMarkButton: UIButton = {
        let button = UIButton()
        button.setImage(UIImage(systemName: Constants.Images.bookmarkIcon), for: .normal)
        button.tintColor = Constants.Colors.searchButtonTintColor
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.imageView?.contentMode = .scaleAspectFit
        return button
    }()
    
    let plusButton: UIButton = {
        let button = UIButton()
        button.setImage(UIImage(systemName: "plus"), for: .normal)
        button.tintColor = Constants.Colors.searchButtonTintColor
        button.contentHorizontalAlignment = .fill
        button.contentVerticalAlignment = .fill
        button.imageView?.contentMode = .scaleAspectFit
        return button
    }()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        delegate = self
        configureNavigationBar()
        
        configureUI()
    }
    
    private func configureUI() {
        configureSearchButton()
        configureBookMarkButton()
        configurePlusButton()
    }
    
    private func configureNavigationBar() {
        navigationBar.barTintColor = .white
        navigationBar.shadowImage = UIImage()
        let appearance = UINavigationBarAppearance()

        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = .white
        appearance.titleTextAttributes = [
            .foregroundColor: UIColor.black,
            .font: FontManager.shared.font(for: .titleLbel)
        ]
        
        appearance.largeTitleTextAttributes = [
            .foregroundColor: UIColor.black,
            .font: FontManager.shared.font(for: .largeTitleLabel)
        ]
        appearance.shadowColor = .clear
        
        navigationBar.standardAppearance = appearance
        navigationBar.compactAppearance = appearance
        navigationBar.scrollEdgeAppearance = appearance
        navigationBar.prefersLargeTitles = true
        navigationBar.barStyle = .default
    }
    
    private func configureSearchButton() {
        navigationBar.addSubview(searchButton)

        searchButton.alpha = 1.0

        searchButton.setWidth(Constants.Dimensions.searchButtonSize)
        searchButton.setHeight(Constants.Dimensions.searchButtonSize)

        searchButton.pinBottom(to: navigationBar.bottomAnchor, Constants.Dimensions.searchButtonBottomMargin)
        searchButton.pinRight(to: navigationBar.trailingAnchor, Constants.Dimensions.searchButtonRightMargin)

        searchButton.addTarget(self, action: #selector(searchButtonPressed(_:)), for: .touchUpInside)
    }
    
    private func configureBookMarkButton() {
        navigationBar.addSubview(bookMarkButton)

        bookMarkButton.alpha = 0.0
        bookMarkButton.isHidden = true

        bookMarkButton.setWidth(Constants.Dimensions.bookMarkkButtonSize)
        bookMarkButton.setHeight(Constants.Dimensions.bookMarkkButtonSize)

        bookMarkButton.pinBottom(to: navigationBar.bottomAnchor, Constants.Dimensions.searchButtonBottomMargin)
        bookMarkButton.pinRight(to: navigationBar.trailingAnchor, Constants.Dimensions.searchButtonRightMargin)

        bookMarkButton.addTarget(self, action: #selector(bookMarkButtonPressed(_:)), for: .touchUpInside)
    }
    
    private func configurePlusButton() {
        navigationBar.addSubview(plusButton)

        plusButton.alpha = 0.0
        plusButton.isHidden = true

        plusButton.setWidth(Constants.Dimensions.bookMarkkButtonSize)
        plusButton.setHeight(Constants.Dimensions.bookMarkkButtonSize)

        plusButton.pinBottom(to: navigationBar.bottomAnchor, Constants.Dimensions.searchButtonBottomMargin)
        plusButton.pinRight(to: navigationBar.trailingAnchor, Constants.Dimensions.searchButtonRightMargin)

        plusButton.addTarget(self, action: #selector(plusButtonPressed(_:)), for: .touchUpInside)
    }
    
    @objc private func searchButtonPressed(_ sender: UIButton) {
        searchButtonPressed?(sender)
    }
    
    @objc private func bookMarkButtonPressed(_ sender: UIButton) {
        bookMarkButtonPressed?(sender)
    }
    
    @objc private func plusButtonPressed(_ sender: UIButton) {
        plusButtonPressed?(sender)
    }
}

extension NavigationBarViewController : UINavigationControllerDelegate {
    func navigationController(
        _ navigationController: UINavigationController,
        willShow viewController: UIViewController,
        animated: Bool
    ) {
        let isAuthenticated = authManager.isAuthenticated
        let shouldShowBookMark = (viewController is WithBookMarkButton) && isAuthenticated
        
        guard let coordinator = navigationController.transitionCoordinator else {
            self.searchButton.alpha = (viewController is WithSearchButton) ? 1.0 : 0.0
            self.searchButton.isHidden = (viewController is WithSearchButton) ? false : true
            self.plusButton.alpha = (viewController is WithPlusButton) ? 1.0 : 0.0
            self.plusButton.isHidden = (viewController is WithPlusButton) ? false : true
            self.bookMarkButton.alpha = shouldShowBookMark ? 1.0 : 0.0
            self.bookMarkButton.isHidden = !shouldShowBookMark
            return
        }
        
        coordinator.animateAlongsideTransition(in: navigationBar, animation: { _ in
            self.searchButton.isHidden = false
            self.bookMarkButton.isHidden = false
            self.plusButton.isHidden = false
            self.searchButton.alpha = (viewController is WithSearchButton) ? 1.0 : 0.0
            self.plusButton.alpha = (viewController is WithPlusButton) ? 1.0 : 0.0
            self.bookMarkButton.alpha = shouldShowBookMark ? 1.0 : 0.0
            if let tabBarVC = self.tabBarController as? TabBarViewController {
                tabBarVC.customTabBar.alpha = (viewController is NonTabBarVC) ? 0.0 : 1.0
            }
        }, completion: { context in
            self.searchButton.isHidden = (viewController is WithSearchButton) ? false : true
            self.plusButton.isHidden = (viewController is WithPlusButton) ? false : true
            self.bookMarkButton.isHidden = !shouldShowBookMark
            if context.isCancelled,
               let fromVC = context.viewController(forKey: .from) {
                self.searchButton.alpha = (fromVC is WithSearchButton) ? 1.0 : 0.0
                self.plusButton.alpha = (fromVC is WithPlusButton) ? 1.0 : 0.0
                self.bookMarkButton.alpha = (fromVC is WithBookMarkButton) && isAuthenticated ? 1.0 : 0.0
                if let tabBarVC = self.tabBarController as? TabBarViewController {
                    tabBarVC.customTabBar.alpha = (fromVC is NonTabBarVC) ? 0.0 : 1.0
                }
            }
        })
    }
    
    func setupBindings() {
        authManager.isAuthenticatedPublisher
            .receive(on: DispatchQueue.main)
            .sink { [weak self] isAuth in
                guard
                    let self = self,
                    let topVC = self.topViewController
                else { return }
                let shouldShowBookMark = (topVC is WithBookMarkButton) && isAuth
                self.bookMarkButton.alpha = shouldShowBookMark ? 1.0 : 0.0
                self.bookMarkButton.isHidden = !shouldShowBookMark
            }
            .store(in: &cancellables)
    }
}
