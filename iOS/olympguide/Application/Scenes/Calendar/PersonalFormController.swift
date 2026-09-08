import UIKit

// Shared native form controls for calendar entries and existing diploma details.
class PersonalFormController: UIViewController {
    let stack = UIStackView()
    var inputs: [String:UITextField] = [:]
    var choices: [String:String] = [:]
    var pickers: [String:UIDatePicker] = [:]
    var change: (() -> Void)?
    var save: (() -> Void)?
    private let scroll = UIScrollView()
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        scroll.translatesAutoresizingMaskIntoConstraints = false; view.addSubview(scroll)
        stack.axis = .vertical; stack.spacing = 18; stack.translatesAutoresizingMaskIntoConstraints = false; scroll.addSubview(stack)
        NSLayoutConstraint.activate([scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor), scroll.bottomAnchor.constraint(equalTo: view.keyboardLayoutGuide.topAnchor),scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor),scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor),stack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor,constant:20),stack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor,constant:-30),stack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor,constant:20),stack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor,constant:-20),stack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor,constant:-40)])
        navigationItem.rightBarButtonItem = UIBarButtonItem(title:"Сохранить",style:.done,target:self,action:#selector(submit))
    }
    @objc private func submit(){view.endEditing(true);save?()}
    func value(_ key:String)->String { inputs[key]?.text?.trimmingCharacters(in:.whitespacesAndNewlines) ?? choices[key] ?? "" }
    func label(_ text:String){let l=UILabel();l.text=text;l.font = .preferredFont(forTextStyle:.body);l.numberOfLines=0;stack.addArrangedSubview(l)}
    @discardableResult func field(_ key:String,_ title:String,_ value:String="",keyboard:UIKeyboardType = .default)->UITextField{
        label(title);let f=UITextField();f.text=value;f.placeholder=title;f.borderStyle = .roundedRect;f.keyboardType=keyboard;f.font = .preferredFont(forTextStyle:.body);f.addAction(UIAction{[weak self] _ in self?.change?()},for:.editingChanged);inputs[key]=f;stack.addArrangedSubview(f);return f
    }
    func choice(_ key:String,_ title:String,_ options:[(String,String)],_ selected:String){
        label(title);let b=UIButton(type:.system);b.contentHorizontalAlignment = .left;b.titleLabel?.numberOfLines=0;b.titleLabel?.font = .preferredFont(forTextStyle:.body)
        choices[key]=selected;b.setTitle(options.first{$0.0==selected}?.1 ?? "Не указано",for:.normal);b.showsMenuAsPrimaryAction=true
        b.menu=UIMenu(children:options.map { value,text in UIAction(title:text){[weak self,weak b] _ in self?.choices[key]=value;b?.setTitle(text,for:.normal);self?.change?()} });stack.addArrangedSubview(b)
    }
    func picker(_ key:String,_ title:String,_ mode:UIDatePicker.Mode,_ date:Date,_ zone:TimeZone){
        label(title);let picker=UIDatePicker();picker.datePickerMode=mode;picker.preferredDatePickerStyle = .compact;picker.locale=Locale(identifier:"ru_RU");picker.timeZone=zone;picker.date=date;pickers[key]=picker;stack.addArrangedSubview(picker)
    }
    func showError(_ message:String){let alert=UIAlertController(title:"Не удалось сохранить",message:message,preferredStyle:.alert);alert.addAction(UIAlertAction(title:"Понятно",style:.default));present(alert,animated:true)}
    func mutation(_ endpoint:String,method:HTTPMethod,body:[String:Any],done:@escaping()->Void){
        navigationItem.rightBarButtonItem?.isEnabled=false
        NetworkService.shared.request(endpoint:endpoint,method:method,queryItems:nil,body:body,shouldCache:false){[weak self](result:Result<BaseServerResponse,NetworkError>) in
            self?.navigationItem.rightBarButtonItem?.isEnabled=true
            switch result {case .success:done();case .failure(let e):self?.showError(e.localizedDescription)}
        }
    }
}
