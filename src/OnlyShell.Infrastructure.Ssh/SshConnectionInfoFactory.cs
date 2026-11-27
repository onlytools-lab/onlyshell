using OnlyShell.Core.Hosts;
using Renci.SshNet;
using Renci.SshNet.Security;

namespace OnlyShell.Infrastructure.Ssh;

public static class SshConnectionInfoFactory
{
    public static ConnectionInfo Create(HostProfile host, string? secret)
    {
        AuthenticationMethod authenticationMethod;
        if (host.AuthenticationMethod == SshAuthenticationMethod.PrivateKey)
        {
            if (string.IsNullOrWhiteSpace(host.PrivateKeyPath) || !File.Exists(host.PrivateKeyPath))
                throw new FileNotFoundException("找不到主机配置中的 SSH 私钥文件。", host.PrivateKeyPath);

            var keyFile = new PrivateKeyFile(host.PrivateKeyPath, secret ?? string.Empty);
            authenticationMethod = new PrivateKeyAuthenticationMethod(host.UserName, new PreferredPrivateKeySource(keyFile));
        }
        else
        {
            authenticationMethod = new PasswordAuthenticationMethod(host.UserName, secret ?? string.Empty);
        }

        var connectionInfo = new ConnectionInfo(host.HostName, host.Port, host.UserName, authenticationMethod)
        {
            Timeout = TimeSpan.FromSeconds(15),
            RetryAttempts = 2
        };
        return connectionInfo;
    }

    private sealed class PreferredPrivateKeySource(PrivateKeyFile keyFile) : IPrivateKeySource
    {
        // Try RSA SHA-2 before legacy SHA-1: some servers close the connection
        // immediately when an ssh-rsa authentication request is rejected.
        public IReadOnlyCollection<HostAlgorithm> HostKeyAlgorithms { get; } = keyFile.HostKeyAlgorithms
            .OrderBy(algorithm => algorithm.Name == "ssh-rsa" ? 1 : 0)
            .ToArray();
    }
}
