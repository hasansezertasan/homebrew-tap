class Hwid < Formula
  include Language::Python::Virtualenv

  desc "Cross-platform hardware ID extraction using native OS detection"
  homepage "https://github.com/hasansezertasan/hwid"
  url "https://files.pythonhosted.org/packages/82/f5/196121ee79989da46195e88db54218d392895b153d0d1fb59658aec3b0d6/hwid-0.3.0.tar.gz"
  sha256 "9304cf1f0f667a524c89073514a052c8ea7574da3b743884570b0a5e91a5b0b0"
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
