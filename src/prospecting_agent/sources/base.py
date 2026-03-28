from __future__ import annotations

from abc import ABC, abstractmethod

from prospecting_agent.models import Company, Contact, ICP


class CompanySource(ABC):
    name = "base_company_source"

    @abstractmethod
    def find_companies(self, icp: ICP) -> list[Company]:
        raise NotImplementedError


class ContactSource(ABC):
    name = "base_contact_source"

    @abstractmethod
    def find_contacts(self, icp: ICP, companies: list[Company]) -> list[Contact]:
        raise NotImplementedError
