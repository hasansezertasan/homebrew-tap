class Hwid < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform hardware ID extraction using native OS detection"
  homepage "https://github.com/hasansezertasan/hwid"
  url "https://files.pythonhosted.org/packages/b7/2d/0c1a3b54610a5b21404dc826638de61ef138953fb2fafd74ccf929a2f1bd/hwid-0.3.1.tar.gz"
  sha256 "727df06e17e009a0ca1c6111e259eb0819e79b1fdfcc54961f344110fa2fa0bc"
  license "MIT"

  livecheck do
    url :stable
    strategy :pypi
  end

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "HWID:", shell_output("#{bin}/hwid")
  end
end
