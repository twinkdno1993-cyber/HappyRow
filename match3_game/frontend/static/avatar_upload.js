async function uploadAvatar(file) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert('Please login first');
        return null;
    }
    
    // В реальном проекте нужно загружать файл на сервер
    // Здесь упрощенная версия — конвертируем в base64
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async function(e) {
            const base64 = e.target.result;
            
            try {
                const response = await fetch('http://localhost:8000/api/avatar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ avatar_url: base64 })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    resolve(data.avatar_url);
                } else {
                    reject('Upload failed');
                }
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function setupAvatarUpload() {
    const avatarInput = document.getElementById('avatar-input');
    if (avatarInput) {
        avatarInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                try {
                    const avatarUrl = await uploadAvatar(file);
                    const avatarImg = document.getElementById('avatar-img');
                    if (avatarImg) {
                        avatarImg.src = avatarUrl;
                    }
                    alert('Avatar updated successfully!');
                } catch (err) {
                    alert('Failed to update avatar');
                }
            }
        });
    }
}