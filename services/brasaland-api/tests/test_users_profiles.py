import pytest
from fastapi import HTTPException

from src.brasaland_api import auth


def create_user(email: str) -> auth.UserInDB:
    return auth.create_user_in_db(
        auth.UserCreate(email=email, password="secure-pass-123", name="Original")
    )


def make_admin(user: auth.UserInDB) -> auth.UserInDB:
    auth.get_users_table().update({"role": auth.Role.admin.value}, doc_ids=[int(user.id)])
    return auth.get_user_by_id(user.id)


def test_user_endpoints_create_list_and_get_without_password(isolated_user_store) -> None:
    created = auth.create_user(
        auth.UserCreate(email="new@example.com", password="secure-pass-123")
    )

    listed = auth.list_users(current_user=auth.get_user_by_id(created.id))
    fetched = auth.get_user(created.id, current_user=auth.get_user_by_id(created.id))

    assert created.email == "new@example.com"
    assert listed == [created]
    assert fetched == created
    assert "password" not in created.model_dump()


def test_get_user_handles_invalid_and_missing_ids(isolated_user_store) -> None:
    assert auth.get_user_by_id("not-a-number") is None

    with pytest.raises(HTTPException) as error:
        auth.get_user("999", current_user=create_user("current@example.com"))

    assert error.value.status_code == 404
    assert error.value.detail == "Usuario no encontrado"


def test_owner_updates_email_and_password(isolated_user_store) -> None:
    owner = create_user("owner@example.com")

    updated = auth.update_user(
        owner.id,
        auth.UserUpdate(email="updated@example.com", password="new-pass-123"),
        current_user=owner,
    )

    assert updated.email == "updated@example.com"
    assert auth.authenticate_user("updated@example.com", "new-pass-123") is not None
    assert auth.authenticate_user("updated@example.com", "secure-pass-123") is None


def test_update_rejects_other_user_and_non_admin_role_change(
    isolated_user_store,
) -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")

    with pytest.raises(HTTPException) as forbidden_other:
        auth.update_user_in_db(
            owner.id, auth.UserUpdate(email="stolen@example.com"), other
        )
    with pytest.raises(HTTPException) as forbidden_role:
        auth.update_user_in_db(
            owner.id, auth.UserUpdate(role=auth.Role.admin), owner
        )

    assert forbidden_other.value.status_code == 403
    assert forbidden_role.value.status_code == 403


def test_admin_changes_role_but_duplicate_email_is_rejected(
    isolated_user_store,
) -> None:
    admin = make_admin(create_user("admin@example.com"))
    target = create_user("target@example.com")
    create_user("existing@example.com")

    promoted = auth.update_user_in_db(
        target.id, auth.UserUpdate(role=auth.Role.manager), admin
    )

    assert promoted.role == auth.Role.manager
    with pytest.raises(HTTPException) as duplicate:
        auth.update_user_in_db(
            target.id, auth.UserUpdate(email="existing@example.com"), admin
        )
    assert duplicate.value.status_code == 400


def test_delete_user_also_deletes_profile(isolated_user_store) -> None:
    owner = create_user("owner@example.com")

    auth.delete_user(owner.id, current_user=owner)

    assert auth.get_user_by_id(owner.id) is None
    assert auth.get_profile_by_user_id(owner.id) is None


def test_delete_rejects_unauthorized_or_missing_user(isolated_user_store) -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")

    with pytest.raises(HTTPException) as forbidden:
        auth.delete_user_in_db(owner.id, other)
    with pytest.raises(HTTPException) as missing:
        auth.delete_user_in_db("999", other)

    assert forbidden.value.status_code == 403
    assert missing.value.status_code == 404


def test_profile_endpoints_get_and_partially_update(isolated_user_store) -> None:
    user = create_user("profile@example.com")

    original = auth.get_my_profile(current_user=user)
    updated = auth.update_my_profile(
        auth.ProfileUpdate(phone="+57 300 000 0000"), current_user=user
    )

    assert original.name == "Original"
    assert updated.name == "Original"
    assert updated.phone == "+57 300 000 0000"


def test_profile_update_creates_missing_profile(isolated_user_store) -> None:
    user = create_user("profile@example.com")
    profiles = auth.get_profiles_table()
    profiles.remove(doc_ids=[1])

    created = auth.update_profile_in_db(
        user.id, auth.ProfileUpdate(name="Recreated")
    )

    assert created.user_id == user.id
    assert created.name == "Recreated"


def test_get_profile_endpoint_rejects_missing_profile(isolated_user_store) -> None:
    user = create_user("profile@example.com")
    auth.get_profiles_table().remove(doc_ids=[1])

    with pytest.raises(HTTPException) as error:
        auth.get_my_profile(current_user=user)

    assert error.value.status_code == 404
    assert error.value.detail == "Perfil no encontrado"